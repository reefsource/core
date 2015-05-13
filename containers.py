# @author:  Gunnar Schaefer, Kevin S. Hahn

import logging
log = logging.getLogger('scitran.api')

import os
import bson
import json
import pytz
import hashlib
import jsonschema

import tempdir as tempfile

import base
import util
import users


FILE_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'File',
    'type': 'object',
    'properties': {
        'name': {
            'title': 'Name',
            'type': 'string',
        },
        'ext': {
            'title': 'Extension',
            'type': 'string',
        },
        'size': {
            'title': 'Size',
            'type': 'integer',
        },
        'sha1': {
            'title': 'SHA-1',
            'type': 'string',
        },
        'type': {
            'title': 'Type',
            'type': 'string',
        },
        'kinds': {
            'title': 'Kinds',
            'type': 'array',
        },
        'state': {
            'title': 'State',
            'type': 'array',
        },
    },
    'required': ['name', 'ext', 'size', 'sha1', 'type', 'kinds', 'state'],
    'additionalProperties': False
}

FILE_UPLOAD_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Upload',
    'type': 'object',
    'properties': {
        'files': {
            'title': 'Files',
            'type': 'array',
            'items': FILE_SCHEMA,
            'uniqueItems': True,
        },
    },
    'required': ['files'],
    'additionalProperties': False,
}

FILE_ACCESS_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'File Download',
    'anyOf': [
        {
            'type': 'object',
            'properties': {
                'type': {
                    'title': 'Type',
                    'type': 'string',
                },
                'kinds': {
                    'title': 'Kinds',
                    'type': 'array',
                },
                'state': {
                    'title': 'State',
                    'type': 'array',
                },
            },
            'required': ['type', 'kinds', 'state'],
        },
        {
            'type': 'object',
            'properties': {
                'name': {
                    'title': 'Type',
                    'type': 'string',
                },
                'ext': {
                    'title': 'Type',
                    'type': 'string',
                },
            },
            'required': ['name'],
        },
    ],
}


def fixup_timestamps(container): # FIXME this method should not have to exist
    if 'timestamp' in container:
        container_timezone = pytz.timezone(container.get('timezone', None) or 'UTC')
        container['timestamp'] = container_timezone.localize(container['timestamp']).isoformat()
        container['timezone'] = container_timezone.zone


class ContainerList(base.RequestHandler):

    def _get(self, query, projection, admin_only=False):
        if self.public_request:
            query['public'] = True
        else:
            projection['permissions'] = {'$elemMatch': {'_id': self.uid, 'site': self.source_site}}
            if not self.superuser_request:
                if admin_only:
                    query['permissions'] = {'$elemMatch': {'_id': self.uid, 'site': self.source_site, 'access': 'admin'}}
                else:
                    query['permissions'] = {'$elemMatch': {'_id': self.uid, 'site': self.source_site}}
        containers = list(self.dbc.find(query, projection))
        for container in containers:
            container['_id'] = str(container['_id'])
            fixup_timestamps(container)
        return containers


class Container(base.RequestHandler):

    def _get(self, _id, min_role=None, filename=None, perm_only=False, dbc=None, dbc_name=None):
        dbc = dbc or self.dbc
        dbc_name = dbc_name or self.__class__.__name__
        container = dbc.find_one({'_id': _id}, ['permissions'] if perm_only else None)
        if not container:
            self.abort(404, 'no such ' + dbc_name)
        user_perm = util.user_perm(container['permissions'], self.uid, self.source_site)
        if self.public_request:
            ticket_id = self.request.get('ticket')
            if ticket_id:
                ticket = self.app.db.downloads.find_one({'_id': ticket_id})
                if not ticket: # FIXME need better security
                    self.abort(404, 'no such ticket')
                if ticket['target'] != _id or ticket['filename'] != filename:
                    self.abort(400, 'ticket not for this resource')
            elif not container.get('public', False):
                self.abort(403, 'this ' + dbc_name + ' is not public')
            del container['permissions']
        elif not self.superuser_request:
            if not user_perm:
                self.abort(403, self.uid + ' does not have permissions on this ' + dbc_name)
            if min_role and users.INTEGER_ROLES[user_perm['access']] < users.INTEGER_ROLES[min_role]:
                self.abort(403, self.uid + ' does not have at least ' + min_role + ' permissions on this ' + dbc_name)
            if user_perm['access'] != 'admin': # if not admin, mask permissions of other users
                container['permissions'] = [user_perm]
        if self.request.get('paths').lower() in ('1', 'true'):
            for fileinfo in container['files']:
                fileinfo['path'] = str(_id)[-3:] + '/' + str(_id) + '/' + fileinfo['name'] + fileinfo['ext']
        container['_id'] = str(container['_id'])
        fixup_timestamps(container) # FIXME WTF?
        return container, user_perm

    def put(self, _id):
        json_body = self.validate_json_body(_id, ['project'])
        self._get(_id, 'admin' if 'permissions' in json_body else 'rw', perm_only=True)
        self.update_db(_id, json_body)
        return json_body

    def validate_json_body(self, _id, oid_keys=[]):
        try:
            json_body = self.request.json_body
            jsonschema.validate(json_body, self.put_schema)
        except (ValueError, jsonschema.ValidationError) as e:
            self.abort(400, str(e))
        if 'permissions' in json_body and json_body['permissions'] is None:
            json_body.pop('permissions')
        for key in oid_keys:
            if key in json_body:
                json_body[key] = bson.ObjectId(json_body[key])
        return json_body

    def update_db(self, _id, json_body):
        self.dbc.update({'_id': _id}, {'$set': util.mongo_dict(json_body)})

    def file(self, cid, filename):
        _id = bson.ObjectId(cid)
        if self.request.method == 'GET':
            container, _ = self._get(_id, 'ro', filename)
            return self._get_file(_id, container, filename)
        elif self.request.method in ['POST', 'DELETE']:
            container, _ = self._get(_id, 'rw', filename)
            return self._get_file(_id, container, filename)
        elif self.request.method == 'PUT':
            container, _ = self._get(_id, 'rw', filename)
            return self._put_file(_id, container, filename)
        else:
            self.abort(405)

    def _get_file(self, _id, container, filename):
        """Download or delete one file."""
        # FIXME:
        # we need a genral way to ask for a single file from a zip file
        # that works for tiles as well as for dicoms

        for fileinfo in container.get('files', []):
            if fileinfo['name'] == filename:
                break
        else:
            self.abort(404, 'no such file')
        filepath = os.path.join(self.app.config['data_path'], str(_id)[-3:] + '/' + str(_id), filename)
        if self.request.method == 'GET':
            self.response.app_iter = open(filepath, 'rb')
            self.response.headers['Content-Length'] = str(fileinfo['size']) # must be set after setting app_iter
            if self.request.get('view').lower() in ['1', 'true']:
                self.response.headers['Content-Type'] = fileinfo.get('mimetype', 'application/octet-stream')
            else:
                self.response.headers['Content-Type'] = 'application/octet-stream'
                self.response.headers['Content-Disposition'] = 'attachment; filename="' + filename + '"'
        elif self.request.method == 'POST':
            ticket = util.download_ticket('file', _id, filename, fileinfo['size'])
            tkt_id = self.app.db.downloads.insert(ticket)
            return {'ticket': tkt_id}
        elif self.request.method == 'DELETE':
            r = self.dbc.update_one({'_id': _id}, {'$pull': {'files': {'name': filename}}})
            if r.modified_count != 1:
                self.abort(400) # FIXME need better error checking
            if os.path.exists(filepath):
                os.remove(filepath)
                log.info('removed file ' + filepath)
            else:
                log.warning(filepath + ' does not exist')
        else:
            self.abort(405)

    def _put_file(self, _id, container, filename):
        """Receive a targeted processor or user upload."""
        #if not self.uid and not self.drone_request:
        #    self.abort(402, 'uploads must be from an authorized user or drone')
        if 'Content-MD5' not in self.request.headers:
            self.abort(400, 'Request must contain a valid "Content-MD5" header.')
        flavor = self.request.get('flavor', 'data')
        if flavor not in ['data', 'attachment']:
            self.abort(400, 'Query must contain flavor parameter: "file" or "attachment".')
        with tempfile.TemporaryDirectory(prefix='.tmp', dir=self.app.config['upload_path']) as tempdir_path:
            filepath = os.path.join(tempdir_path, filename)
            success, sha1sum = util.receive_stream_and_validate(self.request.body_file, filepath, self.request.headers['Content-MD5'])
            if not success:
                self.abort(400, 'Content-MD5 mismatch.')
            filesize = os.path.getsize(filepath)
            datainfo = {
                    'fileinfo': {
                        'filename': filename,
                        'filesize': filesize,
                        'filehash': sha1sum,
                        'flavor': flavor,
                        },
                    }
            log.info('Received    %s [%s] from %s' % (filename, util.hrsize(filesize), self.request.user_agent)) # FIXME should log IP not user agent
            util.commit_file(self.dbc, _id, datainfo, filepath, self.app.config['data_path'])

    def get_tile(self, cid):
        """fetch info about a tiled tiff, or retrieve a specific tile."""
        _id = bson.ObjectId(cid)
        container, _ = self._get(_id, 'ro')  # need at least read access to view tiles
        montage_info = None
        for f in container.get('files'):
            if f['kinds'] == ['montage'] and f['ext'] == '.zip':
                montage_info = f
                break
        if not montage_info:
            self.abort(404, 'montage zip not found')
        fn = montage_info['name'] + montage_info['ext']
        fp = os.path.join(self.app.config['data_path'], cid[-3:], cid, fn)
        z = self.request.get('z')
        x = self.request.get('x')
        y = self.request.get('y')
        if not (z and x and y):
            return util.get_info(fp)
        else:
            self.response.content_type = 'image/jpeg'
            tile = util.get_tile(fp, int(z), int(x), int(y))
            if tile:
                self.response.write(tile)

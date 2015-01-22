# @author:  Gunnar Schaefer

import logging
log = logging.getLogger('nimsapi')

import bson.json_util

import data
import data.medimg

import base


class Projects(base.ContainerList):

    """/projects """

    def __init__(self, request=None, response=None):
        super(Projects, self).__init__(request, response)
        self.dbc = self.app.db.projects

    def count(self):
        """Return the number of Projects."""
        self.response.write(self.dbc.count())

    def post(self):
        """Create a new Project."""
        self.response.write('projects post\n')

    def get(self):
        """Return the User's list of Projects."""
        query = {'group._id': self.request.get('group')} if self.request.get('group') else {}
        projection = {'group': 1, 'name': 1, 'notes': 1}
        projects = self._get(query, projection, self.request.get('admin').lower() in ('1', 'true'))
        if self.debug:
            for proj in projects:
                pid = str(proj['_id'])
                proj['details'] = self.uri_for('project', pid=pid, _full=True) + '?' + self.request.query_string
                proj['sessions'] = self.uri_for('sessions', pid=pid, _full=True) + '?' + self.request.query_string
        return projects

    def groups(self):
        """Return the User's list of Project Groups."""
        return {p['group']['_id']: p['group'] for p in self.get()}.values()


class Project(base.Container):

    """/projects/<pid> """

    json_schema = {
        '$schema': 'http://json-schema.org/draft-04/schema#',
        'title': 'Project',
        'type': 'object',
        'properties': {
            '_id': {
            },
            'site': {
                'type': 'string',
            },
            'site_name': {
                'title': 'Site',
                'type': 'string',
            },
            'permissions': {
                'title': 'Permissions',
                'type': 'object',
                'minProperties': 1,
            },
            'files': {
                'title': 'Files',
                'type': 'array',
                'items': base.Container.file_schema,
                'uniqueItems': True,
            },
        },
        'required': ['_id', 'group', 'name'], #FIXME
    }

    def __init__(self, request=None, response=None):
        super(Project, self).__init__(request, response)
        self.dbc = self.app.db.projects

    def schema(self, *args, **kwargs):
        return super(Project, self).schema(data.medimg.medimg.MedImgReader.project_properties)

    def get(self, pid):
        """Return one Project, conditionally with details."""
        _id = bson.ObjectId(pid)
        proj = self._get(_id)
        proj['site'] = self.app.config['site_id']
        proj['site_name'] = self.app.config['site_name']
        if self.debug:
            proj['sessions'] = self.uri_for('sessions', pid=pid, _full=True) + '?' + self.request.query_string
        return proj

    def put(self, pid):
        """Update an existing Project."""
        _id = bson.ObjectId(pid)
        self._get(_id, 'modify')
        updates = {'$set': {'_id': _id}, '$unset': {'__null__': ''}}
        for k, v in self.request.params.iteritems():
            if k in ['notes']:
                if v is not None and v != '':
                    updates['$set'][k] = v # FIXME: do appropriate type conversion
                else:
                    updates['$unset'][k] = None
        self.dbc.update({'_id': _id}, updates)

    def delete(self, pid):
        """Delete an Project."""
        self.abort(501)
# Summary

This are the main component deployed on the Amazon EC2 instance:
* NGINX web server, serving the API and the frontend UI
* Mongo Service, run on the default port 27017
* API run using uwsgi on port 5001
* UI code, located at `/var/www/coralreef`
* Mongo connector that listen to changes to the job table and start a docker container for each new job
* docker (standard installation for ubuntu to run the docker container for the computations)

# Starting up the system

## BEFORE STARTUP

nginx and the mongo daemon are run as services. Check that they are running:

```sudo service nginx status
sudo service mongodb status
```
If they are not running:
```sudo service nginx start
sudo service mongodb start
```

## API
To start the API, you should run the following commands:
```
workon scitran-core
cd ~/core
nohup uwsgi --socket :5001 --master --wsgi-file bin/api.wsgi -H /home/ubuntu/.virtualenvs/scitran-core --env SCITRAN_PERSISTENT_DB_URI=mongodb://localhost:27017/scitran-core > ../uwsgi.log &
```


## MONGO

to access the mongo database:

```
ubuntu@ip-172-31-61-167:~$ mongo
```

Example operations from the mongo shell.

### CHECK THE CONFIG/JOBS
```javascript
use scitran-core
db.singletons.findOne({'_id':'config'})
db.singletons.update({'_id':'config'}, {$set: {'core.drone_secret':'coralhero2'}})
db.singletons.update({'_id':'config'}, {$set: {'auth.client_id':'198434096526-c806a42elrrhvl89g6b581tmjvbonu3n.apps.googleusercontent.com'}})
db.singletons.update({'_id':'config'}, {$set: {'auth.client_secret':'/home/ubuntu/client_secret_198434096526-c806a42elrrhvl89g6b581tmjvbonu3n.apps.googleusercontent.com.json'}})
var jobs = db.jobs.find()
jobs.forEach(printjson); // print all the results
```

### DELETE EVERYTHING EXCEPT CONFIG ====
```javascript
use scitran-core
db.jobs.drop()
db.projects.drop()
db.sessions.drop()
db.acquisitions.drop()
```


## MONGO CONNECTOR

```
workon scitran-core
cd ~/engine_connector
PYTHONPATH=. nohup mongo-connector -m ip-172-31-61-167:27017 -d engine_simulator -n 'scitran-core.jobs' > ../mongo-connector.log &
```

# Custom configurations you need to be aware of

## drone secret

this is the set in the mongo collection `singletons` in the record with `_id == 'config'`

## gears

to configure a gear there are two things to do:
1) add a rule in the record of the mongo collection singletons with _id == 'rule'
2) add a record in the collection `gears`:
example
```javascript
{
    "_id" : ObjectId("589a20976d241844112871ef"),
    "gear" : {
        "inputs" : {
            "analyzeRAWImage" : {
                "base" : "file",
                "type" : {
                    "enum" : [
                        "gopro"
                    ]
                }
            }
        },
        "name" : "analyzeRAWImage"
    }
}
```

## nginx

The nginx config can be found at /etc/nginx/nginx.conf
Essentially it does two things:
- Serve the API
- Serve the frontend content

## mongo connector

The mongo connector listens to the mongo oplog.
Runs some computation and then upload files to the API.
For the last step we need a folder to store the results of the computation, the drone secret and the nginx local endpoint to upload the files.
This is configured in engine_simulator.py

# TESTING

## ACCESSING THE WEBSITE

This trick will allow you to access the website without changing the global DNS record for coralreefsource.org (changing your local DNS)
```
sudo vi /etc/hosts
add a line with
\<ip ec2 instance\> coralreefsource.org
```

Afterwards you can restore your configuration by removing that line.
Before changing /etc/hosts make a backup of the file to avoid unwanted changes.

## JUPYTER NOTEBOOKS
For the Python savvy, I've written some Jupyter notebooks showing example queries (used in practice to configure the system).

```
ssh -i ~/.ssh/Dailin_Website.pem -L 8888:localhost:8888 ubuntu@ec2-184-72-114-85.compute-1.amazonaws.com
cd scripts
workon scripts
jupyter notebook
# on your local machine navigate to the link with the token shown in the logs
```







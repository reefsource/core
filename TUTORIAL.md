# General Description

The data in Scitran Core is organized using the group, project, session, acquisition hierarchy.
In coralreef we will have only one group and one project for each user.
We will then create one session for each album the user wants to have.
Each album will contain multilple images. For each of them, there will be one acquisition.

# Admin Queries

## create a user

curl -X POST http://localhost/api/users?root=true -k -H Authorization:<AUTHORIZATION_TOKEN> -d '{
    "_id": "user@test.com",
    "firstname": "User",
    "lastname": "Test"
}'

## create a group

This group already exists
```
curl -X POST http://localhost/api/groups?root=true -k -H Authorization:<AUTHORIZATION_TOKEN> -d '{
    "name": "Coral Reef",
    "_id": "coralreef"
}'
```
## create a project for the user

This suppose the existence of the group coralreef:

```
curl -X POST http://localhost/api/projects?root=true -k -H Authorization:<AUTHORIZATION_TOKEN> -d '{
    "label": "user_project",
    "group": "coralreef"
}'
```
# User queries

## get the user projects
```
curl http://localhost/api/projects -k -H Authorization:<AUTHORIZATION_TOKEN>
```
## create an album (session)

This suppose the existence of the project with id "58a3b61bdc313a776756bb5a"


```
curl -X POST http://localhost/api/sessions -k -H Authorization:<AUTHORIZATION_TOKEN> -d '{
    "project": "58a3b61bdc313a776756bb5a",
    "label": "myAlbum"
}'
```

## list all the albums (sessions)

```
curl http://localhost/api/sessions -k -H Authorization:<AUTHORIZATION_TOKEN>
```

## list all the images (acquisitions) in an album

This suppose the existence of a session with id "58a3b61bdc313a776756bda3"

```
curl http://localhost/api/sessions/58a3b61bdc313a776756bda3/acquisitions -k -H Authorization:<AUTHORIZATION_TOKEN>
```


## create an acquisition and upload a file

This suppose the existence of a session with id "58a3b61bdc313a776756bda3":
```
curl -X POST http://localhost/api/acquisitions -k -H Authorization:<AUTHORIZATION_TOKEN> -d '{
    "session": "58a3b61bdc313a776756bda3",
    "label": "gopro"
}'
```

the response to the previous request contains the acquisition id. Let say it is "58a3b61bdc313a776756b456"
```
METADATA='{"type":"gopro"}'
curl -F "file=@GOPR0063.GPR" -F "metadata=$METADATA" -H Authorization:<AUTHORIZATION_TOKEN> https://localhost:8443/api/acquisitions/58a3b61bdc313a776756b456/files -k
```

## download a file
```
curl https://localhost:8443/api/acquisitions/58a3b61bdc313a776756b456/files/GOPR0063.GPR -k -H Authorization:<AUTHORIZATION_TOKEN>
```

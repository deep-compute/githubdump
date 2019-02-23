# gitdump

`gitdump` is a python module/service which is used to store the issues, issue comments of an repository from github of an user.

## prerequisite
* Python 2.7
* User personal accesstoken [clik here to generate token](https://github.com/settings/tokens/new).
   * **Note**: please, generate token based on the requirements with read access for repository and organisation.

## Installation

```bash
git clone https://github.com/deep-compute/githubdump.git
cd githubdump
```

```bash
pip install -e .
```

## Command to run gitdump
- Command format
  ```
  gitdump run -auth '<access_token>' -repos '<repo_full_name,..>' -status_path <directory_location> -target     forwarder=gitdump.messagestore.SQLiteStore:db_name=<db_name>:table_name=<table_name>
  ```
- Example:
  ```
  gitdump run -auth '0f5133209c7dba72234742a7e810d4c7f46dfe0fe' -repos 'deepcompute/githubdump' -status_path /tmp/ -target     forwarder=gitdump.messagestore.SQLiteStore:db_name=Github_dump:table_name=git_test
  ```
**Note**: When you run the above command it will get the issues that are opened in the repository and store it in the db, but it will not give the real time messages when you opened an new issue/comment.In order to achieve the realtime sync with this service we need to configure github webhooks.
Go to repository settings page and click on webhooks

![](https://i.imgur.com/MXjYv50.png)

Its recomended to select the individual events instead of selecting all events

### Arguments
- `auth`    : User access token.(eg : 0f5133209c7dba72234742a7e810d4c7f46dfe0fe)
- `repos`   : Github repositories from which issue information needs to get stored.
   - `Expected formats` :
      ```     
      1. `<username>/<repository>`     (In case of repository is owned by user eg: goutham9032/dummyrepo)
      2. `<organisation>/<repository>` (In case of repository is owned by organisation eg: deepcompute/githubdump)
      ```
- `status_path` : location where the last issue information will be stored (default : /tmp/)
- `target`      : Database to which the json responses/issue info to be stored.
   - `Supported Databses` :
   ```bash
   1. Sqlite
   2. MongoDb
   ```
   - `Expected Format`:
   ```bash
   forwarder=gitdump.messagestore.SQLiteStore:db_name=<db_name>:table_name=<table_name>
   forwarder=gitdump.messagestore.MongoStore:db_name=<db_name>:collection=<table_name>
   ```



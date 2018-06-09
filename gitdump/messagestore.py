import json


import sqlite3
from deeputil import Dummy
from pymongo import MongoClient, DESCENDING

DUMMY_LOG = Dummy

class SQLiteStore(object):

    def __init__(self, db_name="Githu",
                table_name="github_dump",
                log=DUMMY_LOG):

        self.db_name = db_name
        self.table_name = table_name
        self.log = log

        self.con = sqlite3.connect(db_name, check_same_thread=False,
                                  isolation_level=None)
        self.db = self.con.cursor()
        self.db.execute("CREATE TABLE if not exists '%s'(id text UNIQUE,\
                         record text, issue_id text, issue_ts text, comment_ts text)" % (self.table_name))

    def insert_msg(self, record):
        doc = record.get('comment',{}).get('updated_at',
                         record['issue']['created_at'])
        try:
           self.db.execute("INSERT INTO {t} VALUES (?, ?, ?, ?, ?)".format(t=self.table_name),
                           (record['id'], json.dumps(record), str(record['issue']['id']),
                            str(record['issue']['updated_at']), str(doc)))
           self.log.info('Msg inserted in sqlite db', msg_id=record['id'])
        except Exception as e:
           self.log.exception(e)

    def check_issue_in_db(self, issue):
        records = self.db.execute('select issue_ts,comment_ts from %s where \
                              issue_id=%s order by comment_ts desc limit 1' \
                              %(self.table_name, issue['issue']['id']))

        count = 0
        for record in records:
            count += 1
            last_cmnt_time = record[1]

            # if records present,but there might be changes in the issue
            if issue['issue']['updated_at'] != last_cmnt_time:
                return 1, last_cmnt_time

            # if records present no changes related to issue
            return 1, 0

        # if no records related to particular issue
        if count is 0:
            return 0, 0


class MongoStore(object):

    def __init__(self, db_name, collection_name, log=DUMMY_LOG):
        self.db_name = db_name
        self.collection_name = collection_name
        self.log = log
        self.client = MongoClient()
        self.db = self.client[self.db_name][self.collection_name]

    def insert_msg(self, msg):
        self.db.update({'id': msg['id']}, msg, upsert=True)
        self.log.info('Msg inserted in monog db', msg_id=msg['id'])


    def check_issue_in_db(self, issue):
        records = self.db.find({"issue.id": issue['issue']['id']},
                               {"comment": 1})\
            .sort("comment.updated_at", DESCENDING).limit(1)

        # if no records related to particular issue
        if records.count() is 0:
            return 0, 0

        # if records present,checking whether changes  are there in the issue
        for record in records:
            iss_time = issue['issue']['updated_at']
            cmnt_time = record.get('comment', {}).get('updated_at',
                        issue['issue']['created_at'])

            if iss_time != cmnt_time:
                return 1, cmnt_time

        # if records present no changes related to issue
        return 1, 0

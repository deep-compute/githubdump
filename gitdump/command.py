import json
import threading

import tornado.httpserver
import tornado.ioloop
import tornado.web
from basescript import BaseScript

import util
from messagestore import *
from githubhistory import GithubHistory


class RequestHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)

        git = GithubWebhookScript().get_git_obj()

        # gets unique hash key and append with webhook record and store in db
        record = git.get_key(data)
        record.update(data)
        git.write_message(record)

        log = self.application.log
        log.info("Github webhooks key", msg_id=record["id"])


class GithubWebhookScript(BaseScript):

    DESC = "A tool to get the data from github and store it in mongodb"

    def _parse_msg_target_arg(self, t):
        """
        :param t : str
        :rtype : str, dict

        Eg:
        t = 'forwarder=githubdump.messagestore.SQLiteStore:db_name=github_sqlite:table_name=github_dump_sqlite'
        return
             path = githubdump.messagestore.SQLiteStore
             args = {'db_name': 'github_sqlite', 'table_name': 'github_dump_sqlite'}
        """
        self.log.debug("fun : parse msg target arguments")

        path, args = t.split(":", 1)
        path = path.split("=")[1]
        args = dict(a.split("=", 1) for a in args.split(":"))
        args["log"] = self.log

        return path, args

    def msg_store(self):
        self.log.debug("fun : msg store")

        targets = []
        for t in self.args.target:
            imp_path, args = self._parse_msg_target_arg(t)
            target_class = util.load_object(imp_path)
            target_obj = target_class(**args)
            targets.append(target_obj)

        return targets

    def run(self):
        self.log.debug("fun : run")

        th = threading.Thread(target=self.get_git_obj().start)
        th.daemon = True
        th.start()
        self.thread_watch_gmail = th
        self.listen_realtime()

    def listen_realtime(self):
        self.log.debug("fun : tornodo listen")

        self.log.info("Running tornodo on the machine")
        app = tornado.web.Application(handlers=[(r"/", RequestHandler)])
        app.log = self.log
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.listen(self.args.tornodo_port)
        tornado.ioloop.IOLoop.instance().start()

    def get_git_obj(self):
        self.log.debug("fun : get git obj")

        targets = self.msg_store()
        return GithubHistory(
            auth_token=self.args.access_token,
            repos=self.args.repos_list,
            status_path=self.args.status_path,
            targets=targets,
            log=self.log,
        )

    def define_args(self, parser):
        # github arguments
        parser.add_argument(
            "-auth",
            "--access_token",
            metavar="usr_access_token",
            required=True,
            help="access token to authenticate github account",
        )
        parser.add_argument(
            "-repos",
            "--repos_list",
            metavar="repositories",
            nargs="?",
            default=None,
            help="repos to be stored in the db",
        )
        # diskdict arguments
        parser.add_argument(
            "-status_path",
            "--status_path",
            metavar="status_path",
            default=None,
            help="File path where the status of gmail \
                            messages needs to be stored.",
        )

        # database arguments
        parser.add_argument(
            "-target",
            "--target",
            nargs="+",
            help='format for Mongo: store=<MongoStore-classpath>:db_name=<database-name>:collection_name=<collection-name> \
                format for SQLite: store=<SQLiteStore-classpath>:host=<hostname>:port=<port-number>:db_name=<db-name>:table_name=<table-name>"',
        )

        # tornodo arguments
        parser.add_argument(
            "-tp",
            "--tornodo_port",
            metavar="tornodo_port",
            nargs="?",
            default=5000,
            help="port in which tornodo needs to run",
        )


def main():
    GithubWebhookScript().start()

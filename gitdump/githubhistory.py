import time
import hashlib
from copy import deepcopy
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from ConfigParser import _Chainmap as ChainMap

from github import Github
from deeputil import Dummy
from diskdict import DiskDict

DUMMY_LOG = Dummy()


class GithubHistory(object):

    """
    This is the main class you instantiate to access the Github API v3 and store all msgs in the db.

    """

    def __init__(
        self,
        auth_token=None,
        repos=None,
        status_path="/tmp/",
        targets=None,
        log=DUMMY_LOG,
    ):

        self.git = Github(auth_token)
        self.log = log
        self.repos = repos
        self.targets = targets
        self.store = None
        self.dd = DiskDict(status_path + "disk.dict")
        self._pool = ThreadPool()

    def get_repo_obj(self, repo_fullname):
        """
        :params repo_fullname : string
        :rtype: :class:`github.Repository.Repository`

        >>> obj = GithubHistory()
        >>> obj.get_repo_obj('org/reponame')
        Repository(full_name=None)

        """
        self.log.debug("fun : get repo obj")

        return self.git.get_repo(str(repo_fullname))

    def get_repos_list(self):
        """
        :rtype: :class:`github.PaginatedList.PaginatedList` of :class:`github.Repository.Repository`
        or
        :rtype: [class:`github.Repository.Repository`,..]

        >>> from mock import Mock
        >>> obj = GithubHistory()
        >>> m=Mock(obj.repos)
        >>> obj.repos=m.return_value='org/repo1,org/repo2'
        >>> obj.get_repos_list()
        [Repository(full_name=None), Repository(full_name=None)]

        """
        self.log.debug("fun : get repos list")

        if self.repos:
            return [self.get_repo_obj(repo) for repo in self.repos.split(",")]

        return self.git.get_user().get_repos()

    def get_raw_data(self, obj):
        """
        Gets raw json from the obj

        :param obj: class github
        :rtype: dict

        >>> obj = GithubHistory()
        >>> class test(object):
        ...    __dict__ = {'_rawData':{'id':'123456'}}
        ...
        >>> obj.get_raw_data(test())
        {'id': '123456'}

        """
        self.log.debug("fun : get raw data")

        for key, value in obj.__dict__.items():
            if key is "_rawData":
                return value

    def merge_dict(self, *args):
        """
        :params args: dict
        :rtype: dict

        >>> obj = GithubHistory()
        >>> obj.merge_dict({'a':1,'b':2},{'c':3,'d':4})
        {'a': 1, 'c': 3, 'b': 2, 'd': 4}

        """
        self.log.debug("fun : chain dict or merge dict")

        return dict(ChainMap(*args))

    def get_key(self, record):
        """
        :params record: dict
        :rtype: dict

        >>> obj = GithubHistory()
        >>> obj.get_key({'repository':{'updated_at':'21-04-14'},'issue':{'updated_at':'21-04-14'},'comment':{'updated_at':'21-04-14'}})
        {'id': '1c4882d4c922bcfdc070de97de03706c9276f8eb'}
        >>> obj.get_key({'repository':{'updated_at':'21-04-14'},'issue':{},'comment':{}})
        {'id': '8acfc9c43a5c9f64ee2070007591811f4048c907'}

        """
        self.log.debug("fun : get hash key")

        key = "%s%s%s" % (
            record.get("repository", {}).get("updated_at", 0),
            record.get("issue", {}).get("updated_at", 0),
            record.get("comment", {}).get("updated_at", 0),
        )

        # TODO: Need to add repo id
        return {"id": hashlib.sha1(key).hexdigest()}

    def send_msgs_to_target(self, target, msg):
        """
        :param target: db obj
        :param msg: dict

        """
        self.log.debug("send msgs to tatgets")

        target.insert_msg(msg)

    def write_message(self, msg):
        """
        :param msg: dict

        """
        self.log.debug("write msgs in db")

        if self.targets:
            fn = self.send_msgs_to_target

            jobs = []
            for t in self.targets:
                jobs.append(self._pool.apply_async(fn, (t, deepcopy(msg))))

            for j in jobs:
                j.wait()

    def store_record(self, repo, issue=None, comment=None):
        """
        :param repo:    class 'github.Repository.Repository'
        :param issue:   class 'github.Issue.Issue'
        :param comment: class 'github.IssueComment.IssueComment'

        >>> obj = GithubHistory()
        >>> class repo(object):
        ...      __dict__ = { '_rawData' : { 'id' : 1234 }}
        ...      class owner(object):
        ...          type = 'user'
        ...
        >>> class issue(object):
        ...      __dict__ = {'_rawData':{'id':5678}}
        ...
        >>> class comment(object):
        ...      __dict__ = {'_rawData':{'id':91011}}
        ...
        >>> obj.store_record(repo(), issue(), comment())
        {'comment': {'id': 91011}, 'issue': {'id': 5678}, 'id': '8aefb06c426e07a0a671a1e2488b4858d694a730', 'repository': {'id': 1234}}

        """
        self.log.debug("fun : store record")

        iss = cmnt = {}
        rp = self.get_repo_dict(repo)

        if issue:
            iss = self.get_issue_dict(issue)

        if issue and comment:
            cmnt = self.get_comment_dict(comment)

        record = self.merge_dict(rp, iss, cmnt)
        record.update(self.get_key(record))

        self.write_message(record)
        return record

    def get_repo_dict(self, repo):
        """
        :param repo: class 'github.Repository.Repository'
        :rtype: dict

        >>> from mock import Mock
        >>> class repo(object):
        ...     __dict__ = {'_rawData':{'id':'12345', 'name':'abcd'}}
        ...     class owner(object):
        ...         type = 'Organization'
        ...         login = 'orgname'
        ...
        >>> class org(object):
        ...     __dict__ = {'_rawData':{'id':'12345'}}
        ...
        >>> obj=GithubHistory()
        >>> obj.git.get_organization = Mock(obj.git.get_organization,return_value=org())
        >>> obj.get_repo_dict(repo())
        {'organization': {'id': '12345'}, 'repository': {'id': '12345', 'name': 'abcd'}}

        """
        self.log.debug("fun : get repo dict")

        org_dict = {}

        if repo.owner.type == "Organization":
            org = self.git.get_organization(str(repo.owner.login))
            org_dict = {"organization": self.get_raw_data(org)}

        repo_dict = {"repository": self.get_raw_data(repo)}
        return self.merge_dict(org_dict, repo_dict)

    def get_issue_dict(self, issue):
        """
        :param issue: class 'github.Issue.Issue'
        :rtype: dict

        >>> from mock import Mock
        >>> obj = GithubHistory()
        >>> class issue(object):
        ...      __dict__ = {'_rawData':{'id':123456}}
        ...
        >>> obj.get_issue_dict(issue())
        {'issue': {'id': 123456}}

        """
        self.log.debug("fun : get issue dict")

        return {"issue": self.get_raw_data(issue)}

    def get_time(self, _time):
        """
        :param _time: string
        :rtype: datetime.datetime

        >>> obj = GithubHistory()
        >>> obj.get_time('2018-02-15T09:17:49Z')
        datetime.datetime(2018, 2, 15, 9, 17, 50)

        """
        self.log.debug("fun : get api time format")

        return datetime.strptime(_time, "%Y-%m-%dT%H:%M:%SZ") + timedelta(seconds=1)

    def get_comment_dict(self, cmnt):
        """
        :param cmnt:class 'github.IssueComment.IssueComment'
        :rtype: dict

        >>> from mock import Mock
        >>> obj = GithubHistory()
        >>> class comment(object):
        ...      __dict__ = {'_rawData':{'id':123456}}
        ...
        >>> obj.get_comment_dict(comment())
        {'comment': {'id': 123456}}

        """
        self.log.debug("fun : get comment dict")

        return {"comment": self.get_raw_data(cmnt)}

    def check_rate_limit(self):
        """
        Checks no of api calls remaining before going to any function
        if remaining calls of range less than 100 calls wait for some time.

        """
        self.log.debug("fun :check api rate limit")

        remaining, total = self.git.rate_limiting

        if remaining > 1 and remaining < 100:
            expiry = self.git.rate_limiting_resettime
            delay = (expiry - time.time()) + 60
            self.log.info("waiting for " + str(delay) + " sec")
            time.sleep(delay)

    def get_comments(self, repo, issue, changes=None):
        """
        Get comments related to the issue

        :param repo: class 'github.Repository.Repository'
        :param issue: class 'github.Issue.Issue'
        :param changes: string, eg: '2018-02-15T09:17:49Z'

        """
        self.log.debug("fun : get comments")

        self.check_rate_limit()

        # converting issue obj to raw dict as iss_dict
        iss_dict = self.get_raw_data(issue)

        # get issue created time in '%d/%m/%Y' as last_time
        last_time = self.get_time(iss_dict["created_at"])

        # In case there are changes in issue,replace the last_time
        if changes:
            last_time = self.get_time(changes)

        # get and store the comments since issue created or last issue comment updated time(in case of new comments)
        for comment in issue.get_comments(since=last_time):
            self.store_record(repo, issue, comment)

        self.store_record(repo, issue)

    def get_issues(self, repo):
        """
        Get issues related to the input Repository

        :param repo: class 'github.Repository.Repository'

        """
        self.log.debug("fun : get issues")

        self.check_rate_limit()
        for issue in repo.get_issues():

            # getting issue dict from issue obj as iss
            iss = self.get_issue_dict(issue)

            # passing the issue dict and checking in db for issue related records and changes
            # returns (count as 0 or 1),(changes as 0 or time in '2018-02-15T09:17:49Z' format)
            count, changes = self.store.check_issue_in_db(iss)

            # if no records and no changes found realted to issue in db,then get all the comments
            if count is 0:
                self.get_comments(repo, issue)
                continue

            # if records present in db,but the current issue updated time not matched with the last comment
            # updated time in db,so get the msgs from last comment updated time.
            if changes:
                self.get_comments(repo, issue, changes)

    def get_history(self):
        """
        Get user's account repos and from that iterate over issues and comments.
        get_history
           -> repos -> issues -> comments

        """
        self.log.debug("fun : get history")

        for repo in self.get_repos_list():

            # if repo doesn't contain any issues just store the record
            if repo.open_issues is 0:
                self.store_record(repo)
                continue

            # get the issues related to the repo
            self.get_issues(repo)

            # store the status in disk dict
            self.dd["repository"] = repo.full_name

    def start(self):
        self.log.debug("fun : start")

        # create db obj at 0th index from target
        self.store = self.targets[0]

        if "repository" not in self.dd.keys():
            self.get_history()

        # recheck for new messages
        self.get_history()

        self.log.info("Messages stored successfully")

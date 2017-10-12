"""
Collaborator python client through JSON API Web Services
Collaborator Client documentation  .../javadoc/jsonapi/

author: krozin@gmail.com. 2017.
"""

import datetime
import json

import requests

from rtc.log import logger
from rtc import settings


class CollabClient(object):
    """Collaborator client shall ensure connection with Collaborator server """

    def __init__(self, server_uri=settings.COLLAB_URI,
                 user=settings.COLLAB_USER, password=settings.COLLAB_PASS):
        """init
        :param user: str - The user name for the repository
        :param password: str - The password for the repository
        :param server_uri: str - The URI that specifies the JSON WEB server.
        :return: None
        """
        self.user = user
        self.password = password
        self.server_uri = server_uri
        self.headers = {'Content-Type': 'application/json'}
        self.token = None

    def login(self):
        """ Do login
        :param None
        :return: loginTicket or False
        """
        logincmd = "SessionService.getLoginTicket"
        commands = [{"command": logincmd,
                    "args": {"login": self.user, "password": self.password}}]
        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            res = json.loads(r.content)
            token = res[0].get('result', {}).get('loginTicket')
            if token:
                self.token = token
                return token
            error_code = res[0].get('errors', {})[0].get('code')
            error_mess = res[0].get('errors', {})[0].get('message')
            logger.error("code: {}, message= {}".format(error_code,
                                                        error_mess))
        return False

    def create_review(self, title):
        """ Create new code review
        :param title: str Code review title
        :return:
        """
        logincmd = "SessionService.authenticate"
        createcmd = "ReviewService.createReview"
        deadline = datetime.datetime.now()
        deadline += datetime.timedelta(days=3)
        commands = [{"command": logincmd,
                     "args": {"login": self.user, "ticket": self.token}},
                    {"command": createcmd,
                     "args": {"creator": self.user, "title": title,
                              # "deadline": deadline.strftime(
                              #      '%Y-%m-%dT%H:00:00Z'),
                              # "accessPolicy": "PARTICIPANTS",
                              "customFields": [
                                  {"name": "Overview",
                                   "value": ["build check: TBD\n"
                                             "static analysis check: TBD\n"
                                             "unit tests check: TBD\n"
                                             "no open defect check: TBD\n"]}
                              ]}
                     }]

        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            if 'reviewId' in r.content:
                res = json.loads(r.content)
                reviewid = [i.get('result', {}).get('reviewId')
                            for i in res
                            if i.get('result', {}).get('reviewId')][0]
                logger.info("reviewid: {}".format(reviewid))
                return reviewid
        return None

    def delete_review(self, review_id):
        """ Delete code review
            :param review_id: int - review id
            :return True or False
        """
        logincmd = "SessionService.authenticate"
        cmd = "ReviewService.deleteReview"
        commands = [{"command": logincmd,
                     "args": {"login": self.user, "ticket": self.token}},
                    {"command": cmd,
                     "args": {"reviewId": int(review_id)}}]

        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            json.loads(r.content)
            if 'errors' in r.content:
                return False
            return True
        return False

    def add_reviewers(self, reviewid, reviewers):
        """ Add more reviewers
        :param: reviewid - int - review ID
        :param: reviewers - list [{"user":"m1", "role":"REVIEWER"}, ...]
        :return: False or True
        """
        logincmd = "SessionService.authenticate"
        addcmd = "ReviewService.updateAssignments"
        commands = [
            {"command": logincmd,
             "args": {"login": self.user, "ticket": self.token}},
            {"command": addcmd,
             "args": {"reviewId": int(reviewid), "assignments": reviewers}}]
        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            json.loads(r.content)
            if 'errors' in r.content:
                return False
            return True
        return False

    def add_defect(self, reviewid, comment):
        """ Add defect to code review
        :param: reviewid - int - review ID
        :param: comment - str Comment
        :return: False or True
        """
        logincmd = "SessionService.authenticate"
        cmd = "ReviewService.createReviewDefect"
        commands = [
            {"command": logincmd,
             "args": {"login": self.user, "ticket": self.token}},
            {"command": cmd,
             "args": {"reviewId": int(reviewid),
                      "comment": comment,
                      "customFields": [{"name": "Severity",
                                        "value": ["Major"]},
                                       {"name": "Type",
                                        "value": ["Build"]}]
                      }
             }]
        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            res = json.loads(r.content)
            if 'defectId' in r.content:
                defectid = [i.get('result', {}).get('defectId')
                            for i in res
                            if i.get('result', {}).get('defectId')][0]
                logger.info("defectId: {}".format(defectid))
                return defectid
            if 'errors' in r.content:
                logger.error("reviewid: {}"
                             "defectId has not been created".format(reviewid))
                return False
        return False

    def delete_defect(self, defectid):
        """ Delete defect from code review
        :param: defectid - int - defect ID
        :return: False or True
        """
        logincmd = "SessionService.authenticate"
        cmd = "ReviewService.deleteDefect"
        commands = [
            {"command": logincmd,
             "args": {"login": self.user, "ticket": self.token}},
            {"command": cmd,
             "args": {"defectId": int(defectid)}}]
        r = requests.post(self.server_uri,
                          data=json.dumps(commands),
                          headers=self.headers)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code is 200:
            json.loads(r.content)
            if 'errors' in r.content:
                return False
            return True
        return False

    def get_review_by_rtc_changeset(self, scm_id):
        """ code review change list
        :param: reviewid - int - review ID
        :return: False or True
        """
        logincmd = "SessionService.authenticate"
        cmd = "ReviewService.findReviewsByScmChangelist"

        def get_id_by_rtc_changeset(review_phase):
            commands = [
                {"command": logincmd,
                 "args": {"login": self.user, "ticket": self.token}},
                {"command": cmd,
                 "args": {
                     "scmConnectionParameters": [
                         settings.RTC_URI,
                         None,
                         None,
                     ],
                     "scmToken": "RTC",
                     "scmId": scm_id,
                     "reviewPhase": review_phase}
                 }]
            r = requests.post(self.server_uri,
                              data=json.dumps(commands),
                              headers=self.headers)
            logger.debug(r.content)
            logger.debug(r.status_code)
            if r.status_code is 200:
                res = json.loads(r.content)
                if 'errors' in r.content:
                    return False
                elif res[1].get('result', {}).get('reviews', []):
                    review_id = res[1].get(
                        'result', {}).get('reviews', [])[0].get('reviewId')
                    print review_id
                    return review_id
            return False

        res1 = get_id_by_rtc_changeset(review_phase="INSPECTING")
        if res1:
            return res1
        else:
            res2 = get_id_by_rtc_changeset(review_phase="ANNOTATING")
            if res2:
                return res2
            else:
                res3 = get_id_by_rtc_changeset(review_phase="PLANNING")
                if res3:
                    return res3
                else:
                    res4 = get_id_by_rtc_changeset(review_phase="REWORK")
                    if res4:
                        return res4
        return False
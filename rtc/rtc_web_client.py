"""
author: krozin@gmail.com. 2017.
"""

import json

import requests
import xmltodict

HEADERS = {"Accept": "text/html,application/xhtml+xml,"
                     "application/xml;q=0.9,*/*;q=0.8"}


class RTCWebClient(object):
    """Rational team Concept client shall ensure connection with RTC server
       https://jazz.net/wiki/bin/view/Main/ResourceOrientedWorkItemAPIv2
       #Examples_AN1
    """

    def __init__(self, url, user, password, querryid, projectid):
        """init
        :param user: str - The user name for the repository
        :param password: str - The password for the repository
        :param repository_uri: str - The Jazz server URI
        :return: None
        """
        self.user = user
        self.password = password
        self.server_uri = url
        self.querryid = querryid
        self.projectid = projectid
        self.headers = {'Accept': '*/*', 'Content-Type': 'text/xml'}
        self.loginstat = self.login()
        self.project_info = None

    def login(self):
        self._session = requests.session()

        url = '{}/authenticated/identity'.format(self.server_uri)

        headers_global = {'Accept': 'text/xml', 'OSLC-Core-Version': '1.0'}

        r = self._session.get(url, headers=headers_global)

        if r.status_code != 200:
            return False
        elif (r.headers.get('X-com-ibm-team-repository-web-auth-msg') !=
                'authrequired'):
            return False

        url2 = '{}/authenticated/j_security_check'.format(self.server_uri)

        r = self._session.post(url2, data={'j_username': self.user,
                                           'j_password': self.password})

        if r.status_code == 200:
            return True
        return False

    def get_workitem(self, wid):
        url = '{}/oslc/workitems/{}.json'.format(self.server_uri, wid)

        if not self.loginstat:
            return None
        r = self._session.get(url, timeout=30)

        if r.status_code is 200:
            json_data = json.loads(r.content)
            json_data['_found_comments'] = self.get_workitem_comments(
                json_data)
            json_data['_domain'] = self.get_domain(json_data)
            json_data['_project'] = self.get_project(json_data)
            json_data['_team'] = self.get_team(json_data)
            return json_data
        return False

    def get_workitem_full(self, wid):
        """https://local/jazz/service/com.ibm.team.workitem.common.
        internal.rest.IWorkItemRestService/workItemDTO2?
        id=1253911&includeAttributes=true&includeLinks=true&
        includeApprovals=true&includeHistory=true&includeLinkHistory=true"""
        url = ('{}/service/com.ibm.team.workitem.common.internal.rest.'
               'IWorkItemRestService/workItemDTO2?id={}'
               '&includeAttributes=true&includeLinks=true'
               '&includeApprovals=true'
               '&includeHistory=true'
               '&includeLinkHistory=true'.format(self.server_uri, wid))
        # print url
        if not self.loginstat:
            return None
        try:
            r = self._session.get(url, timeout=10.0, allow_redirects=True)
        except (requests.ConnectionError, requests.ReadTimeout,
                requests.Timeout, requests.ConnectTimeout) as e:
            print "exception0: {}".format(e)
            try:
                print url
                r = self._session.get(url, timeout=10.0, allow_redirects=True)
            except Exception as ee:
                print "!!!We've got nothing: {} {}".format(ee, url)
                return None

        if r.status_code == 200:
            res = xmltodict.parse(r.content)
            print "Loaded Workitem #%s" % wid
            return res
        return False

    def _get_json(self, url):
        r = self._session.get(
            url, headers={
                "Accept": "application/x-oslc-cm-changerequest+json"},
            timeout=30)
        if r.status_code != 200:
            raise Exception('%s returned %s' % (url, r.status_code))
        return json.loads(r.content)

    def get_wi_ids_from_querry(self, querryid=None):
        querryid = self.querryid or querryid
        url = ('{}/oslc/queries/{}/rtc_cm:results'
               '?oslc_cm.properties=dc:identifier'.format(self.server_uri,
                                                          querryid))
        if not self.loginstat:
            return None

        ids = []

        next_url = url
        while next_url:
            res = self._get_json(next_url)
            ids.extend(i.get('dc:identifier')
                       for i in res.get('oslc_cm:results'))
            next_url = res.get('oslc_cm:next')

        return ids

    def get_workitems(self, querryid=None):
        ids = self.get_wi_ids_from_querry(querryid)

        workitems = []
        for wiid in ids:
            wk = self.get_workitem_full(wiid)
            if wk:
                workitems.append(wk)
        return workitems

    def get_workitems_to_file(self, filepath, querryid=None, **kwargs):
        its = self.get_workitems(self.querryid or querryid)
        with open(filepath, 'w') as f:
            json.dump(its, f, indent=2)

    def get_domain(self, workitem):
        t = workitem.get('rtc_cm:filedAgainst', {})
        if t:
            domain_uiid = t.get('rdf:resource').split('/')[-1]
            if not hasattr(self.get_domain, domain_uiid):
                res = self.get_domein_info(domain_uiid)
                self.get_domain.__dict__[domain_uiid] = res
                return res
            else:
                return self.get_domain.__dict__[domain_uiid]
        return None

    def get_project(self, workitem):
        t = workitem.get('rtc_cm:projectArea', {})
        if t:
            prj_uiid = t.get('rdf:resource').split('/')[-1]
            if not hasattr(self.get_project, prj_uiid):
                res = self.get_project_area_info(prj_uiid)
                self.get_project.__dict__[prj_uiid] = res
                return res
            else:
                return self.get_project.__dict__[prj_uiid]
        return None

    def get_team(self, workitem):
        t = workitem.get('rtc_cm:teamArea', {})
        if t:
            uiid = t.get('rdf:resource').split('/')[-1]
            if not hasattr(self.get_team, uiid):
                res = self.get_team_info(uiid)
                self.get_team.__dict__[uiid] = res
                return res
            else:
                return self.get_team.__dict__[uiid]
        return None

    def get_workitem_comments(self, workitem):
        comments = []
        if not isinstance(workitem, dict):
            return []
        for i in workitem.get('rtc_cm:comments', []):
            r = self._session.get("{}.json".format(i.get('rdf:resource')))

            if r.status_code is not 200:
                return []
            res = json.loads(r.content)
            creator = res.get(
                'dc:creator', {}).get('rdf:resource').split("/")[-1]
            number = res.get('rdf:resource').split("/")[-1]
            comment = {'number': number,
                       'description': res.get('dc:description').encode("utf8"),
                       'creator': creator,
                       'created': res.get('dc:created'),
                       'url': res.get('rdf:resource')}
            comments.append(comment)
        return comments

    def get_project_enumeration_info(self, projectid=None):
        if projectid is None:
            projectid = self.projectid
        if projectid == self.projectid and self.project_info:
            return self.project_info

        return {'severity_enumeration': self.get_severity_info(projectid),
                'priority_enumeration': self.get_priority_info(projectid),
                'types_enumeration': self.get_type_info(projectid),
                'root_cause_type_enumeration':
                    self.get_rootcause_type_info(projectid),
                'testing_stage_enumeration':
                    self.get_test_stage_info(projectid),
                'defect_workflow':
                    self.get_workflow_info(projectid),
                'feedback_status_enumeration':
                    self.get_ex_feedback_status_info(projectid),
                'issue_occurrence_description_enumeration':
                    self.get_issue_occurrence_info(projectid),
                'issue_severity_description_enumeration':
                    self.get_issue_severity_description_info(projectid),
                'issue_detection_description_enumeration':
                    self.get_issue_detection_description_info(projectid),
                'ryg_status_enumeration':
                    self.get_ryg_status_enumeration_info(projectid),
                'model_year_enumeration': self.get_modelyear_info(projectid),
                'project_area_info': self.get_project_area_info(projectid)}

    def get_severity_info(self, projectid=None):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/severity.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/enumerations/{}/severity.json'.format(
            self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_severity_info, projectid):
            return self.get_severity_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200 and r.content:
            res = json.loads(r.content)
            self.get_severity_info.__dict__[projectid] = res
            return res
        return False

    def get_priority_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/priority.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/enumerations/{}/priority.json'.format(
            self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_priority_info, projectid):
            return self.get_priority_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_priority_info.__dict__[projectid] = res
            return res
        return False

    def get_type_info(self, projectid):
        """https://local/jazz/oslc/types/RTC_PROJECT_ID.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/types/{}.json'.format(self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_type_info, projectid):
            return self.get_type_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_type_info.__dict__[projectid] = res
            return res
        return False

    def get_rootcause_type_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           root_cause_type_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/enumerations/{}/root_cause_type_enumeration.json'
               ''.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_rootcause_type_info, projectid):
            return self.get_rootcause_type_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_rootcause_type_info.__dict__[projectid] = res
            return res
        return False

    def get_test_stage_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           testing_stage_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/enumerations/{}/testing_stage_enumeration.json'.format(
            self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_test_stage_info, projectid):
            return self.get_test_stage_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_test_stage_info.__dict__[projectid] = res
            return res
        return False

    def get_workflow_info(self, projectid):
        """https://local/jazz/oslc/workflows/RTC_PROJECT_ID/states/
           com.pasa.team.workitem.defectWorkflow.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/workflows/{}/states/com.pasa.team.workitem.'
               'defectWorkflow.json'.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_workflow_info, projectid):
            return self.get_workflow_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_workflow_info.__dict__[projectid] = res
            return res
        return False

    def get_ex_feedback_status_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           feedback_status_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/enumerations/{}/feedback_status_enumeration.json'
               ''.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_ex_feedback_status_info, projectid):
            return self.get_ex_feedback_status_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_ex_feedback_status_info.__dict__[projectid] = res
            return res
        return False

    def get_issue_occurrence_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           issue_occurrence_description_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/enumerations/{}/issue_occurrence_description_'
               'enumeration.json'.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_issue_occurrence_info, projectid):
            return self.get_issue_occurrence_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_issue_occurrence_info.__dict__[projectid] = res
            return res
        return False

    def get_issue_severity_description_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           issue_severity_description_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/enumerations/{}/issue_severity_description_'
               'enumeration.json'.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_issue_severity_description_info, projectid):
            return self.get_issue_severity_description_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_issue_severity_description_info.__dict__[projectid] = res
            return res
        return False

    def get_issue_detection_description_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           issue_detection_description_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = ('{}/oslc/enumerations/{}/issue_detection_description_'
               'enumeration.json'.format(self.server_uri, projectid))
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_issue_detection_description_info, projectid):
            return self.get_issue_detection_description_info.__dict__[
                projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_issue_detection_description_info.__dict__[projectid] = res
            return res
        return False

    def get_ryg_status_enumeration_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           ryg_status_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/enumerations/{}/ryg_status_enumeration.json'.format(
            self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_ryg_status_enumeration_info, projectid):
            return self.get_ryg_status_enumeration_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=50)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_ryg_status_enumeration_info.__dict__[projectid] = res
            return res
        return False

    def get_modelyear_info(self, projectid):
        """https://local/jazz/oslc/enumerations/RTC_PROJECT_ID/
           model_year_enumeration.json"""
        if not projectid:
            projectid = self.projectid
        url = '{}/oslc/enumerations/{}/model_year_enumeration.json'.format(
            self.server_uri, projectid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_modelyear_info, projectid):
            return self.get_modelyear_info.__dict__[projectid]

        r = self._session.get(url, headers={"Accept": "*/*", }, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_modelyear_info.__dict__[projectid] = res
            return res
        return False

    def get_domein_info(self, uuid):
        """https://local/jazz/resource/itemOid/com.ibm.team.workitem.Category/
           UUID"""
        url = '{}/resource/itemOid/com.ibm.team.workitem.Category/{}'.format(
            self.server_uri, uuid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_domein_info, uuid):
            return self.get_domein_info.__dict__[uuid]

        r = self._session.get(url, headers=HEADERS, timeout=50)

        if r.status_code is 200:
            res = xmltodict.parse(r.content).get('rtc_cm:Category')
            dres = {'title': res.get('dc:title'),
                    'hierarchicalName': res.get('rtc_cm:hierarchicalName'),
                    'description': res.get('dc:description'),
                    'projectArea': res.get(
                        'rtc_cm:projectArea', {}).get(
                        '@rdf:resource').split('/')[-1],
                    'defaultTeamArea': res.get(
                        'rtc_cm:defaultTeamArea', {}).get(
                        '@rdf:resource').split('/')[-1]}
            self.get_domein_info.__dict__[uuid] = dres
            return dres
        return False

    def get_team_info(self, uuid):
        """https://local/jazz/oslc/teamareas//UUID"""
        url = '{}/oslc/teamareas/{}.json'.format(self.server_uri, uuid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_team_info, uuid):
            return self.get_team_info.__dict__[uuid]

        r = self._session.get(url, headers=HEADERS, timeout=30)

        if r.status_code is 200:
            res = json.loads(r.content)
            dres = {'title': res.get('dc:title'),
                    'description': res.get('dc:description'),
                    'projectArea': res.get(
                        'rtc_cm:projectArea', {}).get(
                        'rdf:resource').split('/')[-1],
                    'members': res.get('rtc_cm:members', {})}
            self.get_team_info.__dict__[uuid] = dres
            return dres
        return False

    def get_team_members(self, team_uuid):
        """https://local/jazz/oslc/teamareas/TEAM_UUID/rtc_cm:members.json"""
        url = '{}/oslc/teamareas/{}/rtc_cm:members.json'.format(
            self.server_uri, team_uuid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_team_members, team_uuid):
            return self.get_team_members.__dict__[team_uuid]

        r = self._session.get(url, headers=HEADERS, timeout=30)
        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_team_members.__dict__[team_uuid] = res
            return res
        return False

    def get_project_area_info(self, uuid):
        """https://local/jazz/oslc/projectareas/_9qwq0PATEeOOedCg5mLUvg.json"""
        url = '{}/oslc/projectareas/{}.json'.format(self.server_uri, uuid)
        print url
        if not self.loginstat:
            return None

        if hasattr(self.get_project_area_info, uuid):
            return self.get_project_area_info.__dict__[uuid]

        r = self._session.get(url, headers=HEADERS, timeout=30)
        print("get_project_area_info: status:{} \nheaders: {} \ncookies: {} "
              "\ncontent={}".format(r.status_code, r.headers, r.cookies,
                                    r.content))
        if r.status_code is 200:
            res = json.loads(r.content)
            self.get_project_area_info.__dict__[uuid] = res
            return res
        return False

    @staticmethod
    def prn_workitem(self, workitem):
        return "\n\nRTCWorkItem: workitemID={}\n" \
               "severity={} priority={} type={} state={}" \
               "\nfound_comments={} \ndomain={} \nproject={} \nteam={}" \
               "\ntitle={} \ndescription={} \nsubject={} \nmodified={} " \
               "\ncreator={} \ncreated={}" \
               "\nfiledAgainst={} \nplannedFor={} \nresolution={} " \
               "\nresolved={} \nfoundIn={}" \
               "\nownedBy={} \nmodifiedBy={} \nresolvedBy={}" \
               "\nprojectArea={} \nteamArea={} \nestimate={} " \
               "\ncorrectedEstimate={} \ntimeSpent={}" \
               "\ndue={} \ncomments={} \nsubscribers={} " \
               "\naffectsExecutionResult={} \nblocksTestExecutionRecord={}" \
               "\nimplementsRequirement={} \ntestedByTestCase={} " \
               "\nrelatedChangeManagement={} \nattachment={}" \
               "\nparent={} \nchildren={} \nrelated={} \nrelatedArtifact={} " \
               "\nblocks={} \ndependsOn={}" \
               "\nduplicates={} \nduplicateOf={} \ncopies={} " \
               "\ncopiedFrom={} \ntextuallyReferenced={}" \
               "\nreportedAgainstBuilds={} \nincludedInBuilds={} " \
               "\nchangeSet={}" \
               "\n".format(
                   workitem.wid, workitem.severity, workitem.priority,
                   workitem.wtype, workitem.state,
                   workitem.found_comments, workitem.domain,
                   workitem.project, workitem.team,
                   workitem.title.encode("utf8"),
                   workitem.description.encode("utf8"),
                   workitem.subject.encode("utf8"),
                   workitem.modified, workitem.creator, workitem.created,
                   workitem.filedAgainst, workitem.plannedFor,
                   workitem.resolution, workitem.resolved, workitem.foundIn,
                   workitem.ownedBy, workitem.modifiedBy, workitem.resolvedBy,
                   workitem.projectArea, workitem.teamArea, workitem.estimate,
                   workitem.correctedEstimate, workitem.timeSpent,
                   workitem.due, workitem.comments, workitem.subscribers,
                   workitem.affectsExecutionResult,
                   workitem.blocksTestExecutionRecord,
                   workitem.implementsRequirement, workitem.testedByTestCase,
                   workitem.relatedChangeManagement, workitem.attachment,
                   workitem.parent, workitem.children, workitem.related,
                   workitem.relatedArtifact, workitem.blocks,
                   workitem.dependsOn, workitem.duplicates,
                   workitem.duplicateOf, workitem.copies, workitem.copiedFrom,
                   workitem.textuallyReferenced,
                   workitem.reportedAgainstBuilds,
                   workitem.includedInBuilds, workitem.changeSet)

    @staticmethod
    def get_workitem_attr_info(self):
        return [
            {'name': 'dc:identifier', 'type': 'Integer',
             'description': 'The work item ID', 'oslc': True},
            {'name': 'dc:type', 'type': 'Type Reference',
             'description': 'The work item type', 'oslc': True},
            {'name': 'dc:title', 'type': 'Medium HTML',
             'description': 'The summary', 'oslc': True},
            {'name': 'dc:description', 'type': 'Large HTML',
             'description': 'The description', 'oslc': True},
            {'name': 'dc:subject', 'type': 'Medium String',
             'description': 'The tags', 'oslc': True},
            {'name': 'dc:modified', 'type': 'Timestamp',
             'description': 'The modification date', 'oslc': True},
            {'name': 'dc:creator', 'type': 'User Reference',
             'description': 'The creator of the work item', 'oslc': True},
            {'name': 'dc:created', 'type': 'Timestamp',
             'description': 'The creation date', 'oslc': False},
            {'name': 'oslc_cm:priority', 'type': 'Literal Reference',
             'description': 'The priority', 'oslc': False},
            {'name': 'oslc_cm:severity', 'type': 'Literal Reference',
             'description': 'The severity', 'oslc': False},
            {'name': 'rtc_cm:filedAgainst', 'type': 'Category Reference',
             'description': 'The category the work item is filed against',
             'oslc': False},
            {'name': 'rtc_cm:plannedFor', 'type': 'Iteration Reference',
             'description': 'The iteration the work item is planned for',
             'oslc': False},
            {'name': 'rtc_cm:state', 'type': 'Status Reference',
             'description':
                'The status of the work item (modifiable via action)',
             'oslc': False},
            {'name': 'rtc_cm:resolution', 'type': 'Resolution Reference',
             'description': 'The resolution of the work item', 'oslc': False},
            {'name': 'rtc_cm:ownedBy', 'type': 'User Reference',
             'description': 'The owner', 'oslc': False},
            {'name': 'rtc_cm:modifiedBy', 'type': 'User Reference',
             'description': 'The user who last modified the work item',
             'oslc': False},
            {'name': 'rtc_cm:resolvedBy', 'type': 'User Reference',
             'description': 'The user who resolved the work item',
             'oslc': False},
            {'name': 'rtc_cm:resolved', 'type': 'Timestamp',
             'description': '   The resolution date', 'oslc': False},
            {'name': 'rtc_cm:foundIn', 'type': 'Deliverable Reference',
             'description': 'The release/deliverable the defect was found in',
             'oslc': False},
            {'name': 'rtc_cm:projectArea', 'type': 'Project Area Reference',
             'description': 'The work items project area', 'oslc': False},
            {'name': 'rtc_cm:teamArea', 'type': 'Team Area Reference',
             'description': 'The work items team area', 'oslc': False},
            {'name': 'rtc_cm:estimate', 'type': 'Long',
             'description': 'The estimated work time in ms', 'oslc': False},
            {'name': 'rtc_cm:correctedEstimate', 'type': 'Long',
             'description': 'The corrected estimate in ms', 'oslc': False},
            {'name': 'rtc_cm:timeSpent', 'type': 'Long',
             'description': 'The time spent working on the item in ms',
             'oslc': False},
            {'name': 'rtc_cm:due', 'type': 'Timestamp',
             'description': 'The due date', 'oslc': False},
            {'name': 'rtc_cm:comments', 'type': 'Comment Collection',
             'description': 'The comments collection (modifiable via POST)',
             'oslc': False},
            {'name': 'rtc_cm:subscribers', 'type': 'User Collection',
             'description': 'The subscriptions', 'oslc': False},
            {'name': 'calm:affectsExecutionResult', 'type': 'Link Collection',
             'description': 'Affected execution results in RQM',
             'oslc': False},
            {'name': 'calm:blocksTestExecutionRecord',
             'type': 'Link Collection',
             'description': 'Blocked test execution records in RQM',
             'oslc': False},
            {'name': 'calm:implementsRequirement',
             'type': 'Link Collection',
             'description': 'Implemented requirements in RRC', 'oslc': False},
            {'name': 'calm:testedByTestCase', 'type': 'Link Collection',
             'description': 'Test cases in RQM', 'oslc': False},
            {'name': 'oslc_cm:relatedChangeManagement',
             'type': 'Link Collection',
             'description': 'Related change requests in CQ', 'oslc': False},
            {'name':
                'rtc_cm:com.ibm.team.workitem.linktype.attachment.attachment',
             'type': 'Link Collection',
             'description': 'Attachments', 'oslc': False},
            {'name':
                'rtc_cm:com.ibm.team.workitem.linktype.parentworkitem.parent',
             'type': 'Link Collection',
             'description':
                'The parent work item (collection size is always 1)',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.parentworkitem'
                     '.children',
             'type': 'Link Collection',
             'description': 'Child work items', 'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.relatedworkitem'
                     '.related',
             'type': 'Link Collection',
             'description': 'Related work items', 'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.relatedartifact'
                     '.relatedArtifact',
             'type': 'Link Collection',
             'description': 'Related artifacts / URIs', 'oslc': False},
            {'name':
                'rtc_cm:com.ibm.team.workitem.linktype.blocksworkitem.blocks',
             'type': 'Link Collection',
             'description': 'Blocked work items', 'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.blocksworkitem'
                     '.dependsOn',
             'type': 'Link Collection',
             'description': 'Blocking work items', 'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.duplicateworkitem'
                     '.duplicates',
             'type': 'Link Collection',
             'description': 'Duplicates of this work item', 'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.duplicateworkitem'
                     '.duplicateOf',
             'type': 'Link Collection',
             'description': 'The work item is a duplicate of these work items',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.copiedworkitem'
                     '.copies',
             'type': 'Link Collection',
             'description': 'The work item was copied to this work item',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.copiedworkitem'
                     '.copiedFrom',
             'type': 'Link Collection',
             'description': 'The work item was copied from this work item',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.workitem.linktype.textualReference'
                     '.textuallyReferenced',
             'type': 'Link Collection',
             'description': 'The work item has textual '
                            'references to these items',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.build.linktype.reportedWorkItems'
                     '.com.ibm.team.build.common.link.reportedAgainstBuilds',
             'type': 'Link Collection',
             'description': 'The builds the work item was filed against',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.build.linktype.includedWorkItems'
                     '.com.ibm.team.build.common.link.includedInBuilds',
             'type': 'Link Collection',
             'description': 'The builds the work item was first included in',
             'oslc': False},
            {'name': 'rtc_cm:com.ibm.team.filesystem.workitems.change_set'
                     '.com.ibm.team.scm.ChangeSet',
             'type': 'Link Collection',
             'description': 'The change sets attached to the work item',
             'oslc': False}
        ]

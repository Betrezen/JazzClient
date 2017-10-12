"""
Nexus client
author: krozin@gmail.com. 2017.
"""

import json
import os
import re

import requests

from rtc.log import logger
from rtc import settings


class Artefact(object):

    def __init__(self, aid, url, repositoryName, componentId,
                 aformat, contentType, size='',
                 lastUpdated=None, lastAccessed=None, blobRef=None,
                 attributes=None):
        if attributes is None:
            attributes = {
                'cache': {'last_verified': None},
                'maven2': {'extension': None,
                           'baseVersion': None,
                           'groupId': None,
                           'classifier': None,
                           'artifactId': None,
                           'version': None,
                           'asset_kind': None},
                'checksum': {'sha1': None, 'md5': None},
                'provenance': {'hashes_not_verified': None},
                'content': {'last_modified': None, 'cache': {}}}
        self.aid = aid
        self.url = url
        self.repositoryName = repositoryName
        self.componentId = componentId
        self.aformat = aformat
        self.contentType = contentType
        self.size = size
        self.lastUpdated = lastUpdated
        self.lastAccessed = lastAccessed
        self.blobRef = blobRef
        self.attributes = attributes
        self.classifier = attributes.get('maven2', {}).get('classifier')
        self.extension = attributes.get('maven2', {}).get('extension')
        self.group = attributes.get('maven2', {}).get('groupId')
        self.version = attributes.get('maven2', {}).get('version')
        self.artifactId = attributes.get('maven2', {}).get('artifactId')
        self.name = url.split('/')[-1]

    def __repr__(self):
        return '{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}'.format(
            self.aid, self.name, self.url, self.repositoryName,
            self.componentId, self.aformat, self.contentType,
            self.size, self.classifier, self.extension, self.group,
            self.version, self.artifactId,
            self.lastUpdated, self.lastUpdated, self.blobRef, self.attributes)


class Component(object):

    def __init__(self, group, name='', version='', classifier='',
                 extension=''):
        self.group = group
        self.name = name
        self.version = version
        self.classifier = classifier or ''
        self.extension = extension or ''

    def __repr__(self):
        return 'Group:{} Name:{} Version:{} Classifier:{} Extension:{}'.format(
            self.group, self.name, self.version, self.classifier,
            self.extension)


class LocalComponent(Component):

    def __init__(self, local_path, group, name=None, version=None,
                 classifier=None, extension=None):
        self.local_path = local_path
        artifact_detected, version_detected, extension_detected = (
            self.get_attr())

        if not name:
            name = artifact_detected
        if not version:
            version = version_detected
        if not extension:
            extension = extension_detected

        super(LocalComponent, self).__init__(group=group,
                                             name=name,
                                             version=version,
                                             classifier=classifier,
                                             extension=extension)

    def get_attr(self):
        base_name = os.path.basename(self.local_path)
        result = re.match(
            '^(?# name)(.*?)-(?=\d)(?# version)(\d.*)\.(?# extension)([^.]+)$',
            base_name)
        if result is None:
            logger.error('Automatic detection of name and/or version '
                         'failed for %s', self.local_path)
            return None, None, None
        name = result.group(1)
        version = result.group(2)
        extension = result.group(3)
        logger.debug('name: {}, version: {}, extension: {}'.format(
            name, version, extension))
        return name, version, extension


class NexusComponent(Component):

    def __init__(self, group, name=None, version=None, classifier=None,
                 extension=None, cformat=None, repositoryName=None, rid=None,
                 url=None):
        super(NexusComponent, self).__init__(group=group,
                                             name=name,
                                             version=version,
                                             classifier=classifier,
                                             extension=extension)
        self.cformat = cformat
        self.rid = rid
        self.repositoryName = repositoryName
        self.url = url

    def __repr__(self):
        return 'Group:{} Name:{} Version:{} Classifier:{} Extension:{} ' \
               'Format:{} ID:{} repositoryName:{} Url:{}'.format(
                   self.group, self.name, self.version, self.classifier,
                   self.extension, self.cformat, self.rid, self.repositoryName,
                   self.url)

    @classmethod
    def cls_from_attr(cls, repositoryName, attr):
        """
        :param repo_id:
        :param coordinates: e.g. 'com.ant:task:1.0.0'
        :return:
        """
        fields = attr.split(':')
        if len(fields) < 3:
            logger.error('Incorrect coordinates, at least group, '
                         'artifact and version are obligatory')
            return None
        group = fields[0]
        artifact = fields[1]
        version = fields[2]
        classifier = None
        extension = None
        if len(fields) > 3:
            classifier = fields[3]
        if len(fields) > 4:
            extension = fields[4]
        return cls(group=group, artifact=artifact, version=version,
                   classifier=classifier, extension=extension,
                   repositoryName=repositoryName)


class NexusClient(object):
    """Nexus client shall ensure connection with Nexus server """

    def __init__(self, server_uri=settings.NEXUS_URI,
                 user=settings.NEXUS_USER, password=settings.NEXUS_PASS):
        """ init
        :param user: str - The user name for the repository
        :param password: str - The password for the repository
        :param server_uri: str - The URI that specifies the WEB server.
        :return: None
        """
        self.user = user
        self.password = password
        self.server_uri = server_uri
        self._repository_url = server_uri
        self._verify_ssl = False
        self.headers = {'Content-Type': 'application/json'}
        self._session = requests.Session()
        self._session.auth = (user, password)

    def search(self, component):
        list_components = []
        headers = {'Content-Type': 'application/json;charset=utf-8',
                   'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate',
                   'X-Nexus-UI': 'true',
                   'X-Requested-With': 'XMLHttpRequest'}
        d = {
            "action": "coreui_Search",
            "method": "read",
            "type": "rpc",
            "tid": 11,
            "data": [
                {
                    "page": 1,
                    "start": 0,
                    "limit": 100,
                    "sort": [{"property": "group", "direction": "ASC"}],
                    "filter": [
                        {"property": "format", "value": "maven2"},
                        {"property": "attributes.maven2.groupId",
                         "value": component.group},
                        {"property": "attributes.maven2.version",
                         "value": component.version},
                        {"property": "attributes.maven2.artifactId",
                         "value": component.name},
                        {"property": "assets.attributes.maven2.extension",
                         "value": component.extension},
                        {"property": "assets.attributes.maven2.classifier",
                         "value": component.classifier}
                    ]
                }
            ]
        }

        search_url = "{}/service/extdirect".format(self.server_uri)
        res = self._session.post(
            search_url, headers=headers, data=json.dumps(d))
        logger.debug(res.content)
        logger.debug(res.status_code)
        if res.status_code == 200:
            result = json.loads(res.content).get("result", {}).get("data")
            if result:
                for i in result:
                    comp = NexusComponent(
                        rid=i.get('id'),
                        group=i.get('group'),
                        repositoryName=i.get('repositoryName'),
                        name=i.get('name'),
                        version=i.get('version'),
                        cformat=i.get('format'))
                    list_components.append(comp)
            return list_components
        return []

    def get_artifacts(self, component):
        list_artefacts = []
        print "Ask{}".format(component)
        headers = {'Content-Type': 'application/json;charset=utf-8',
                   'Accept': '*/*',
                   'Accept-Encoding': 'gzip, deflate',
                   'X-Nexus-UI': 'true',
                   'X-Requested-With': 'XMLHttpRequest'}
        d = {"action": "coreui_Component",
             "method": "readComponentAssets",
             "type": "rpc", "tid": 31,
             "data": [{"page": 1, "start": 0, "limit": 100,
                       "filter": [{"property": "repositoryName",
                                   "value": component.repositoryName},
                                  {"property": "componentId",
                                   "value": component.rid},
                                  {"property": "componentName",
                                   "value": component.name},
                                  {"property": "componentGroup",
                                   "value": component.group},
                                  {"property": "componentVersion",
                                   "value": component.version}]}]}
        search_url = "{}/service/extdirect".format(self.server_uri)
        res = self._session.post(
            search_url, headers=headers, data=json.dumps(d))
        logger.debug(res.content)
        logger.debug(res.status_code)
        if res.status_code == 200:
            result = json.loads(res.content).get("result", {}).get("data")
            if result:
                for i in result:
                    ar = Artefact(aid=i.get('id'), url=i.get('name'),
                                  aformat=i.get('format'),
                                  contentType=i.get('contentType'),
                                  size=i.get('size'),
                                  repositoryName=i.get('repositoryName'),
                                  lastUpdated=i.get('lastUpdated'),
                                  lastAccessed=i.get('lastAccessed'),
                                  blobRef=i.get('blobRef'),
                                  componentId=i.get('componentId'),
                                  attributes=i.get('attributes'))
                    list_artefacts.append(ar)
            return list_artefacts
        return []

    def download(self, component, artefact_name, dirpath):
        """ download file from nexus
            http://nexus3.sde.ttt.ru:8081/repository/PublicNorforge
            /com/avaya/commons/avaya-commons-sandbox-http/1.0/
            fff-commons-sandbox-http-1.0-javadoc.jar
        """
        comp = NexusComponent(group=component.group,
                              name=component.name,
                              version=component.version,
                              classifier=component.classifier,
                              extension=component.extension,
                              repositoryName=component.repositoryName)
        components = self.search(comp)
        if components:
            for i in components:
                artefacts = self.get_artifacts(i)
                for j in artefacts:
                    if j.name == artefact_name and\
                       j.classifier == component.classifier and\
                       j.extension == component.extension:
                        url = "{}/repository/{}/{}".format(
                            self.server_uri, component.repositoryName, j.url)
                        r = self._session.get(url)
                        # logger.debug(r.content)
                        logger.debug(r.status_code)
                        if r.status_code == 200:
                            file_path = os.path.join(dirpath, j.name)
                            with open(file_path, 'wb') as f:
                                f.write(r.raw.read())
                            return True
        return False

    def upload(self, repo, file):
        """ upload file to nexus
        :param str: repo - repository name
        :param file: fileobj - filepath
        :return: True or False
        """
        with open(file, 'rb') as f:
            r = requests.post("{}/{}".format(self.server_uri, repo),
                              auth=(self.user, self.password), data=f)
        logger.debug(r.content)
        logger.debug(r.status_code)
        if r.status_code == 200:
            return True
        return False

"""
Settings python loader for CI
TODO documentation link
"""

import os
import socket

from rtc.log import logger, set_file
from rtc.yamlloader import get_env


filepath = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'settings.conf')
env = get_env(filepath=filepath, attrdict=True)
# print env


##############################
# Common #
##############################
try:
    LOG_FILE = env.common.log_file
except Exception:
    LOG_FILE = 'debug.log'

LOCAL_WORKSPACE_DIR = os.environ.get('WORKSPACE_DIR', os.getcwd())
LOGS_PATH = os.environ.get('LOGS_PATH',
                           os.path.join(LOCAL_WORKSPACE_DIR, 'logs'))
BUILD_PATH = os.environ.get('BUILD_PATH',
                            os.path.join(LOCAL_WORKSPACE_DIR, 'build'))
BUILD_ID = os.environ.get('buildResultUUID', '')

LOG_FILE = os.path.join(LOGS_PATH, LOG_FILE)
CHECK_RESULT_FILE = os.path.join(LOGS_PATH, CHECK_RESULT_FILE)


##############################
# Logging #
##############################
try:
    if not os.path.exists(LOGS_PATH):
        os.mkdir(LOGS_PATH)
except Exception:
    os.mkdir('build')
set_file(LOG_FILE)


##############################
# Services #
##############################
RTC_URI = os.environ.get('repositoryAddress', env.rtc.server_uri.get('host'))

try:
    COLLAB_HOST = env.collaborator.server_uri.get('host')
    COLLAB_PORT = int(env.collaborator.server_uri.get('port'))
    COLLAB_SERVICE = env.collaborator.server_uri.get('service')
    COLLAB_USER = env.collaborator.get('user')
    COLLAB_PASS = env.collaborator.get('passwd')
except Exception:
    COLLAB_HOST = socket.gethostname()
    COLLAB_PORT = 8080
    COLLAB_SERVICE = 'services/json/v1'
    COLLAB_USER = 'user'
    COLLAB_PASS = 'passwd'
COLLAB_URI = "{}:{}/{}".format(COLLAB_HOST, COLLAB_PORT, COLLAB_SERVICE)

CODEREVIEW_FLAG = str(os.environ.get('CODEREVIEW_FLAG'))
if (CODEREVIEW_FLAG == 'True' or
        CODEREVIEW_FLAG == 'true' or
        CODEREVIEW_FLAG == 'None'):
    CODEREVIEW_FLAG = True
else:
    CODEREVIEW_FLAG = False

try:
    NEXUS_HOST = env.nexus.server_uri.get('host')
    NEXUS_PORT = int(env.nexus.server_uri.get('port'))
    NEXUS_SERVICE = env.nexus.server_uri.get('service')
    NEXUS_USER = env.nexus.get('user')
    NEXUS_PASS = env.nexus.get('passwd')
except Exception:
    NEXUS_HOST = socket.gethostname()
    NEXUS_PORT = 8081
    NEXUS_SERVICE = 'repository'
    NEXUS_USER = 'user'
    NEXUS_PASS = 'passwd'
NEXUS_URI = "{}:{}".format(NEXUS_HOST, NEXUS_PORT)


##############################
# Ant #
##############################
DEBUG_CMD = ''
BUILD_ANT_DEBUG_FLAG = str(os.environ.get('BUILD_ANT_DEBUG_FLAG'))
if (BUILD_ANT_DEBUG_FLAG == 'True' or
        BUILD_ANT_DEBUG_FLAG == 'true' or
        BUILD_ANT_DEBUG_FLAG == 'None'):
    DEBUG_CMD = '-d '
try:
    BUILD_TOOLKIT_PATH = os.environ['BUILD_TOOLKIT_PATH']
except Exception:
    BUILD_TOOLKIT_PATH = (
        'C:\\RTC-BuildSystem-Toolkit-Win64-6.0.2\\jazz'
        '\\buildsystem\\buildtoolkit')
BUILD_TOOLKIT_CMD = '-lib ' + BUILD_TOOLKIT_PATH + ' '
BUILD_FILE_CMD = '-buildfile ' + BUILD_ANT_FILE + ' '
ANT_CMD = 'ant ' + DEBUG_CMD + BUILD_TOOLKIT_CMD + BUILD_FILE_CMD


##############################
# Email notify list , env.common.buildEmailListNofify#
##############################
try:
    BUILD_EMAIL_LIST_NOTIFY = env.common.buildEmailListNofify
    if os.environ.get('buildEmailListNofify'):
        BUILD_EMAIL_LIST_NOTIFY = os.environ.get('buildEmailListNofify')
except Exception:
    BUILD_EMAIL_LIST_NOTIFY = 'krozin@gmail.com'

##############################
# Debug #
##############################
#logger.debug("LOCAL_WORKSPACE_DIR={}".format(LOCAL_WORKSPACE_DIR))
#logger.debug("BUILD_PATH={}".format(BUILD_PATH))
#logger.debug("LOGS_PATH={}".format(LOGS_PATH))
#logger.debug("LOG_FILE={}".format(LOG_FILE))
#logger.debug("RTC={}".format(RTC_URI))
#logger.debug("COLLAB={}, USER={}, PASSWD={}".format(
#    COLLAB_URI, COLLAB_USER, COLLAB_PASS))
#logger.debug("NEXUS={}, USER={}, PASSWD={}".format(
#    NEXUS_URI, NEXUS_USER, NEXUS_PASS))
#logger.debug("ANT_CMD={}".format(ANT_CMD))
#logger.debug("WORKSPACE_UUID={}".format(os.environ.get('WORKSPACE_UUID')))
#logger.debug("WORKITEM_UUID={}".format(os.environ.get('WORKITEM_UUID')))
#logger.debug("CHANGESET_UUID={}".format(os.environ.get('CHANGESET_UUID')))
#logger.debug("buildResultUUID={}".format(os.environ.get('buildResultUUID')))
#logger.debug("Path={}".format(os.environ.get('Path')))

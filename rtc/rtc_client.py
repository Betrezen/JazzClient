"""
author: krozin@gmail.com. 2016.

Rational Team Concept python client through scm command line tool

EXAMPLES:
    sudo -E python -c "import rtc_client; cl=rtc_client.RTCClient();
    print '\n'.join([str(i) for i in cl.list_workspaces()])"
    sudo -E python -c "import rtc_client; cl=rtc_client.RTCClient();
    print cl.load_workspace('_-l0BENzWEea9RaEJtJ44rt@repo', '/tmp/111')"
"""

import json
import subprocess
import shlex

from rtc.log import logger
from rtc import settings


class RTCClient(object):
    """Rational team Concept client shall ensure connection with RTC server """

    def __init__(self, repository_uri=settings.RTC_URI,
                 user=None, password=None,
                 scm_cmd='scm'):
        """init
        :param user: str - The user name for the repository
        :param password: str - The password for the repository
        :param repository_uri: str - The URI that specifies the
        location of the repository.
        :return: None
        """
        self.user = user
        self.password = password
        self.repository_uri = repository_uri
        self.scm_cmd = scm_cmd

    def __run_scm(self, cmd, **kwargs):
        """Run command through scm
        :param cmd: list - scm command
        :return: object - data if successful, None otherwise
        """
        ignore_r = kwargs.get('ignore_repo', False)
        if not ignore_r:
            if self.user and self.password:
                run_cmd = "{} {} {} {} {} {} {} {}".format(
                    self.scm_cmd, cmd, '-r', self.repository_uri,
                    '-u', self.user, '-P', self.password)
            else:
                run_cmd = "{} {} {} {}".format(
                    self.scm_cmd, cmd, '-r', self.repository_uri)
        else:
            if self.user and self.password:
                run_cmd = "{} {} {} {} {} {}".format(
                    self.scm_cmd, cmd, '-u', self.user, '-P', self.password)
            else:
                run_cmd = "{} {}".format(self.scm_cmd, cmd)
        args = shlex.split(run_cmd)

        if self.password:
            logger.debug(run_cmd.replace(self.password, '***'))
        else:
            logger.debug(run_cmd)

        code = None
        try:
            pipe = subprocess.Popen(args,
                                    stderr=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
            out, err = pipe.communicate()
            code = pipe.returncode
        except Exception as message:
            logger.debug('{}'.format(message))
            raise Exception('code={} scm command {} '
                            'has failed with the '
                            'message: {}'.format(code, run_cmd, message))

        if (out is None) or code != 0:
            logger.debug("rcode ={} or err ={}".format(code, err))
            raise Exception('scm command {} '
                            'has failed with the '
                            'exception: {}'.format(run_cmd, err))
        return out

    def __list_info(self, command):
        """Try to get list info
        :param command: str - scm command string acceptable for 'list'
        :return: object - output if successful, empty string otherwise
        """
        cmd = 'list {}'.format(command)
        return self.__run_scm(cmd)

    def list_workspaces(self):
        """Try to get list of workspaces
        :param: None
        :return: dict - dict object if successful, {} otherwise
        """
        return json.loads(self.__list_info('workspaces -j'))

    def list_components(self, workspace_uuid):
        """Try to get list of components for required workspace
        :param: None
        :return: dict - dict object if successful, {} otherwise
        """
        return json.loads(self.__list_info(
            'components -j "{}"'.format(workspace_uuid)))

    def load_workspace(self, workspace_uuid, component, local_workspace_dir):
        """Try to load workspace
        :param: workspace_uuid: str - workspace which contents will be
            downloaded
        :param: component: str - component that will be downloaded
        :param: local_workspace_dir: str - local directory to save files to
        :return:None ot True
        """
        cmd = 'load "{}" "{}" -d "{}" -f'.format(
            workspace_uuid, component, local_workspace_dir)
        out = self.__run_scm(cmd)
        if 'Successfully loaded items into' in out:
            return True

    def create_workspace(self, workspace_name, stream=None):
        """Try to create new workspace for required stream
        :param workspace_name: str - name for workspace that will be created
        :param stream: str - stream for which workspace will be created
        :return: None or True
        """
        cmd = 'create workspace "{}"'.format(workspace_name)
        if stream:
            cmd += ' -s "{}"'.format(stream)
        else:
            cmd += ' --empty'
        out = self.__run_scm(cmd)
        if 'successfully created' in out:
            return True

    def delete_workspace(self, workspace_name):
        """Try to delete workspace
        :param workspace_name: str - workspace that will be deleted
        :return: None or True
        """
        cmd = 'delete workspace "{}"'.format(workspace_name)
        out = self.__run_scm(cmd)
        if 'Workspace was successfully deleted' in out:
            return True

    def set_baseline(self, workspace_name, component_name, baseline_name):
        """Try to set baseline for required component
        :param workspace_name: str - workspace for required component
        :param component_name: str - component for which baseline will
            be changed
        :param baseline_name: str - baseline that should be set
        :return: None or True
        """
        cmd = 'set component --baseline "{}" "{}" workspace "{}" "{}"'.format(
            baseline_name, workspace_name,
            workspace_name, component_name)
        out = self.__run_scm(cmd)
        if 'Problem running \'set component\'' not in out:
            return True

    def show_status(self, local_workspace_dir):
        """Try to get info from local workspace
        :param local_workspace_dir: path to loca dir
        :return: None or data
        """
        cmd = 'show status -N -j --xchangeset -d "{}"'.format(
            local_workspace_dir)
        out = self.__run_scm(cmd, ignore_repo=True)
        logger.debug("show_status: {}".format(out))
        return json.loads(out)

    def show_component_attributes(self, component):
        """Try to get component attributes
        :param component: str - target component
        :return: None or data
        """
        cmd = 'show attributes -j -C "{}"'.format(
            component)
        out = self.__run_scm(cmd)
        logger.info("show_component_attributes: {}".format(out))
        return json.loads(out)

    def show_history(self, stream_name, component_name, maximum=10):
        """Show history for component
        :param stream_name: stream or workspace
        :param component_name: component name or uuid
        :param maximum: number of history entries
        :return: None or data
        """
        cmd = 'show history -j -m {} -w "{}" -C "{}"'.format(
            maximum, stream_name, component_name)

        out = self.__run_scm(cmd)
        # logger.debug("show_history: {}".format(out))
        return json.loads(out)

    def get_last_changeset_id_from_component(
            self, stream_name, component_name):
        history = self.show_history(stream_name, component_name, maximum=1)
        return history['changes'][0]['uuid']

    def list_flowtargets(self, local_workspace_dir, target):
        """List flow targets of the workspace or stream

        :param local_workspace_dir: path to loca dir
        :param target: name or UUID of stream or workspace
        """
        cmd = 'list flowtargets -j -d "{}" "{}"'.format(
            local_workspace_dir, target)
        out = self.__run_scm(cmd)
        logger.debug("list flowtargets: {}".format(out))
        return json.loads(out)

    def list_remotefiles(self, target, component, depth=1):
        """Displays the content that are in a repository workspace.

        :param local_workspace_dir: path to loca dir
        :param target: name or UUID of stream or workspace
        :param component: name or UUID of component
        :param depth: The maximum depth at which to query remote
                      paths.
        """
        cmd = 'list remotefiles --depth {} -j -w "{}" "{}"'.format(
            depth, target, component)
        out = self.__run_scm(cmd)
        logger.debug("list flowtargets: {}".format(out))
        return json.loads(out)

    def add_components(self, workspace, components):
        """Adds components to workspace

        :param workspace: name or UUID of workspace
        :param components: list of component names of UUIDs
        """
        cstr = ' '.join('"{}"'.format(c) for c in components)
        cmd = 'add component "{}" {}'.format(workspace, cstr)
        out = self.__run_scm(cmd)
        if 'successfully added' in out:
            return True

    def list_changes(self, changeset_uuid):
        """Try to get list of changes for changeset.

        :param changeset_uuid: UUID of change-set
        """
        # cmd = 'list changes -j {}'.format(changeset_uuid)
        # out = self.__run_scm(cmd)
        return json.loads(self.__list_info('changes -j ' + changeset_uuid))

    def show_component_info(self, component):
        """Show component information.

        :param component: UUID of component
        """
        cmd = 'get attributes -C {} --ownedby  -j'.format(component)
        out = self.__run_scm(cmd)
        return json.loads(out)

    def list_users(self):
        """Try to get list of users.

        :param: None
        """
        return json.loads(self.__list_info('users -j'))

    def get_component_name(self, component_uuid):
        """Show component name by it's uuid.

        :param component_uuid: UUID of component
        """
        cmd = 'show custom-attributes --component {}'.format(component_uuid)
        out = self.__run_scm(cmd)
        component_name = out.split('"')[1]
        return component_name

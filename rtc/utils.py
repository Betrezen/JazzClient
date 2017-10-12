import subprocess

from rtc.log import logger


def str2bool(s):
    return s.lower() in ('true', '1', 'yes')


def nexus_string(str):
    return str.replace(' ', '_').replace('.', '_')


def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazyprop(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazyprop


def run_cmd(cmd, cwd=None):
    logger.debug('command: {}\n'.format(cmd))
    code = None
    try:
        pipe = subprocess.Popen(
            cmd, shell=True, cwd=cwd,
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = pipe.communicate()
        code = pipe.returncode
    except Exception as message:
        logger.debug('{}'.format(message))
        raise Exception('code: {} command: {}'
                        'has failed with the message: {}'.format(
                            code, cmd, message))
    if (out is None) or code != 0:
        logger.debug('output before error: {}\n'.format(out))
        logger.debug('code: {} and error: {}'.format(code, err))
        raise Exception('Command: {} has failed with code: {} and error: {}\n'
                        'Output before error: {}'.format(cmd, code, err, out))
    logger.debug('output: {}\n'.format(out))
    return out

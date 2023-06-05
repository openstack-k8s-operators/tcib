#   Copyright 2015 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
import configparser
import os
import logging
import multiprocessing
import pwd
import re
import shutil
import sys
import tempfile
import yaml

import ansible_runner  # noqa

LOG = logging.getLogger(__name__ + ".utils")
ANSIBLE_HOSTS_FILENAME = "hosts.yaml"
CLOUD_HOME_DIR = os.path.expanduser('~' + os.environ.get('SUDO_USER', ''))


class Pushd(object):
    """Simple context manager to change directories and then return."""

    def __init__(self, directory):
        """This context manager will enter and exit directories.
        >>> with Pushd(directory='/tmp'):
        ...     with open('file', 'w') as f:
        ...         f.write('test')
        :param directory: path to change directory to
        :type directory: `string`
        """
        self.dir = directory
        self.pwd = self.cwd = os.getcwd()

    def __enter__(self):
        os.chdir(self.dir)
        self.cwd = os.getcwd()
        return self

    def __exit__(self, *args):
        if self.pwd != self.cwd:
            os.chdir(self.pwd)


class TempDirs(object):
    """Simple context manager to manage temp directories."""

    def __init__(self, dir_path=None, dir_prefix='tcib', cleanup=True,
                 chdir=True):
        """This context manager will create, push, and cleanup temp directories.
        >>> with TempDirs() as t:
        ...     with open('file', 'w') as f:
        ...         f.write('test')
        ...     print(t)
        ...     os.mkdir('testing')
        ...     with open(os.path.join(t, 'file')) as w:
        ...         print(w.read())
        ...     with open('testing/file', 'w') as f:
        ...         f.write('things')
        ...     with open(os.path.join(t, 'testing/file')) as w:
        ...         print(w.read())
        :param dir_path: path to create the temp directory
        :type dir_path: `string`
        :param dir_prefix: prefix to add to a temp directory
        :type dir_prefix: `string`
        :param cleanup: when enabled the temp directory will be
                         removed on exit.
        :type cleanup: `boolean`
        :param chdir: Change to/from the created temporary dir on enter/exit.
        :type chdir: `boolean`
        """

        # NOTE(cloudnull): kwargs for tempfile.mkdtemp are created
        #                  because args are not processed correctly
        #                  in py2. When we drop py2 support (cent7)
        #                  these args can be removed and used directly
        #                  in the `tempfile.mkdtemp` function.
        tempdir_kwargs = dict()
        if dir_path:
            tempdir_kwargs['dir'] = dir_path

        if dir_prefix:
            tempdir_kwargs['prefix'] = dir_prefix

        self.dir = tempfile.mkdtemp(**tempdir_kwargs)
        self.pushd = Pushd(directory=self.dir)
        self.cleanup = cleanup
        self.chdir = chdir

    def __enter__(self):
        if self.chdir:
            self.pushd.__enter__()
        return self.dir

    def __exit__(self, *args):
        if self.chdir:
            self.pushd.__exit__()
        if self.cleanup:
            self.clean()
        else:
            LOG.warning("Not cleaning temporary directory [ %s ]", self.dir)

    def clean(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        LOG.info("Temporary directory [ %s ] cleaned up", self.dir)


def _encode_envvars(env):
    """Encode a hash of values.
    :param env: A hash of key=value items.
    :type env: `dict`.
    """
    for key, value in env.items():
        env[key] = str(value)
    return env


def makedirs(dir_path):
    """Recursively make directories and log the interaction.
    :param dir_path: full path of the directories to make.
    :type dir_path: `string`
    :returns: `boolean`
    """

    try:
        os.makedirs(dir_path)
    except FileExistsError:
        LOG.debug(
            'Directory "%s" was not created because it already exists.',
            dir_path
        )
        return False

    LOG.debug('Directory "%s" was created.', dir_path)
    return True


def playbook_verbosity(self):
    """Return an integer for playbook verbosity levels.
    :param self: Class object used to interpret the runtime state.
    :type self: Object
    :returns: Integer
    """

    if self.app.options.debug:
        return 3
    if self.app_args.verbose_level <= 1:
        return 0
    return self.app_args.verbose_level


def run_ansible_playbook(playbook, inventory, workdir, playbook_dir=None,
                         connection='smart', output_callback='default',
                         ssh_user='root', key=None, module_path=None,
                         limit_hosts=None, tags=None, skip_tags=None,
                         verbosity=0, quiet=False, extra_vars=None,
                         extra_vars_file=None, gathering_policy='smart',
                         extra_env_variables=None,
                         parallel_run=False,
                         ansible_cfg=None, ansible_timeout=30,
                         reproduce_command=True,
                         timeout=None, forks=None,
                         ignore_unreachable=False):
    """Simple wrapper for ansible-playbook.
    :param playbook: Playbook filename.
    :type playbook: String
    :param inventory: Either proper inventory file, or a coma-separated list.
    :type inventory: String
    :param workdir: Location of the working directory.
    :type workdir: String
    :param playbook_dir: Location of the playbook directory.
                         (defaults to workdir).
    :type playbook_dir: String
    :param connection: Connection type (local, smart, etc).
    :type connection: String
    :param output_callback: Callback for output format. Defaults to
                            "default".
    :type output_callback: String
    :param ssh_user: User for the ssh connection.
    :type ssh_user: String
    :param key: Private key to use for the ssh connection.
    :type key: String
    :param module_path: Location of the ansible module and library.
    :type module_path: String
    :param limit_hosts: Limit the execution to the hosts.
    :type limit_hosts: String
    :param tags: Run specific tags.
    :type tags: String
    :param skip_tags: Skip specific tags.
    :type skip_tags: String
    :param verbosity: Verbosity level for Ansible execution.
    :type verbosity: Integer
    :param quiet: Disable all output (Defaults to False)
    :type quiet: Boolean
    :param extra_vars: Set additional variables as a Dict or the absolute
                       path of a JSON or YAML file type.
    :type extra_vars: Either a Dict or the absolute path of JSON or YAML
    :param extra_vars_file: Set additional ansible variables using an
                            extravar file.
    :type extra_vars_file: Dictionary
    :param gathering_policy: This setting controls the default policy of
                             fact gathering ('smart', 'implicit', 'explicit').
    :type gathering_facts: String
    :param extra_env_variables: Dict option to extend or override any of the
                                default environment variables.
    :type extra_env_variables: Dict
    :param parallel_run: Isolate playbook execution when playbooks are to be
                         executed with multi-processing.
    :type parallel_run: Boolean
    :param ansible_cfg: Path to an ansible configuration file. One will be
                        generated in the artifact path if this option is None.
    :type ansible_cfg: String
    :param ansible_timeout: Timeout for ansible connections.
    :type ansible_timeout: int
    :param reproduce_command: Enable or disable option to reproduce ansible
                              commands upon failure. This option will produce
                              a bash script that can reproduce a failing
                              playbook command which is helpful for debugging
                              and retry purposes.
    :type reproduce_command: Boolean
    :param timeout: Timeout for ansible to finish playbook execution (minutes).
    :type timeout: int
    """

    def _playbook_check(play):
        if not os.path.exists(play):
            play = os.path.join(playbook_dir, play)
            if not os.path.exists(play):
                raise RuntimeError('No such playbook: {}'.format(play))
        LOG.debug('Ansible playbook %s found', play)
        return play

    def _inventory(inventory):
        if inventory:
            if isinstance(inventory, str):
                # check is file path
                if os.path.exists(inventory):
                    return inventory
            elif isinstance(inventory, dict):
                inventory = yaml.safe_dump(
                    inventory,
                    default_flow_style=False
                )
            inv_file = ansible_runner.utils.dump_artifact(
                inventory,
                workdir,
                ANSIBLE_HOSTS_FILENAME)
            os.chmod(inv_file, 0o600)
            return inv_file

    def _running_ansible_msg(playbook, timeout=None):
        if timeout and timeout > 0:
            return ('Running Ansible playbook with timeout %sm: %s' %
                    (timeout, playbook))
        return ('Running Ansible playbook: %s' % playbook)

    def _is_venv():
        return (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and
                 sys.base_prefix != sys.prefix))

    def _get_development_prefix():
        src_file = getattr(sys.modules[__name__], "__file__", "")
        # Remove 'tcib/client/utils.py' from the src_file
        return src_file[:-20]

    if not playbook_dir:
        playbook_dir = workdir

    # Ensure that the ansible-runner env exists
    runner_env = os.path.join(workdir, 'env')
    makedirs(runner_env)

    if extra_vars_file:
        runner_extra_vars = os.path.join(runner_env, 'extravars')
        with open(runner_extra_vars, 'w') as f:
            f.write(yaml.safe_dump(extra_vars_file, default_flow_style=False))

    if timeout and timeout > 0:
        settings_file = os.path.join(runner_env, 'settings')
        timeout_value = timeout * 60
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings_object = yaml.safe_load(f.read())
                settings_object['job_timeout'] = timeout_value
        else:
            settings_object = {'job_timeout': timeout_value}

        with open(settings_file, 'w') as f:
            f.write(yaml.safe_dump(settings_object, default_flow_style=False))

    if isinstance(playbook, (list, set)):
        verified_playbooks = [_playbook_check(play=i) for i in playbook]
        playbook = os.path.join(workdir, 'tcib-multi-playbook.yaml')
        with open(playbook, 'w') as f:
            f.write(
                yaml.safe_dump(
                    [{'import_playbook': i} for i in verified_playbooks],
                    default_flow_style=False
                )
            )

        LOG.info(
            '%s,'
            '  multi-playbook execution: %s,'
            ' Working directory: %s,'
            ' Playbook directory: %s',
            _running_ansible_msg(playbook, timeout),
            verified_playbooks,
            workdir,
            playbook_dir
        )
    else:
        playbook = _playbook_check(play=playbook)
        LOG.info(
            '%s, Working directory: %s, Playbook directory: %s',
            _running_ansible_msg(playbook, timeout),
            workdir,
            playbook_dir
        )

    if limit_hosts:
        LOG.info(
            'Running ansible with the following limit: %s', limit_hosts
        )
    ansible_fact_path = os.path.join(
        os.path.expanduser('~'),
        '.tcib',
        'fact_cache'
    )
    makedirs(ansible_fact_path)

    if not forks:
        forks = min(multiprocessing.cpu_count() * 4, 100)

    env = dict()
    env['ANSIBLE_SSH_ARGS'] = (
        '-o UserKnownHostsFile={} '
        '-o StrictHostKeyChecking=no '
        '-o ControlMaster=auto '
        '-o ControlPersist=30m '
        '-o ServerAliveInterval=64 '
        '-o ServerAliveCountMax=1024 '
        '-o Compression=no '
        '-o TCPKeepAlive=yes '
        '-o VerifyHostKeyDNS=no '
        '-o ForwardX11=no '
        '-o ForwardAgent=yes '
        '-o PreferredAuthentications=publickey '
        '-T'
    ).format(os.devnull)
    env['ANSIBLE_DISPLAY_FAILED_STDERR'] = True
    env['ANSIBLE_FORKS'] = forks
    env['ANSIBLE_TIMEOUT'] = ansible_timeout
    env['ANSIBLE_GATHER_TIMEOUT'] = 45
    env['ANSIBLE_SSH_RETRIES'] = 3
    env['ANSIBLE_PIPELINING'] = True
    env['ANSIBLE_SCP_IF_SSH'] = True
    env['ANSIBLE_REMOTE_USER'] = ssh_user
    env['ANSIBLE_STDOUT_CALLBACK'] = output_callback
    env['ANSIBLE_COLLECTIONS_PATHS'] = '/usr/share/ansible/collections'
    env['ANSIBLE_LIBRARY'] = (
        '/usr/share/ansible/plugins/modules:'
        '/usr/share/ceph-ansible/library:'
        '/usr/share/ansible-modules'
    )
    env['ANSIBLE_LOOKUP_PLUGINS'] = (
        '/usr/share/ansible/plugins/lookup:'
        '/usr/share/ceph-ansible/plugins/lookup'
    )
    env['ANSIBLE_CALLBACK_PLUGINS'] = (
        '/usr/share/ansible/plugins/callback:'
        '/usr/share/ceph-ansible/plugins/callback'
    )
    env['ANSIBLE_ACTION_PLUGINS'] = (
        '/usr/share/ansible/plugins/action:'
        '/usr/share/ceph-ansible/plugins/actions'
    )
    env['ANSIBLE_FILTER_PLUGINS'] = (
        '/usr/share/ansible/plugins/filter:'
        '/usr/share/ceph-ansible/plugins/filter'
    )
    env['ANSIBLE_ROLES_PATH'] = (
        '/usr/share/ansible/roles:'
        '/usr/share/ceph-ansible/roles:'
        '/etc/ansible/roles'
    )
    if _is_venv():
        roles_path = os.path.join(_get_development_prefix(), 'roles')
        env['ANSIBLE_ROLES_PATH'] += ":{}".format(roles_path)
    env['ANSIBLE_RETRY_FILES_ENABLED'] = False
    env['ANSIBLE_HOST_KEY_CHECKING'] = False
    env['ANSIBLE_TRANSPORT'] = connection
    env['ANSIBLE_CACHE_PLUGIN_TIMEOUT'] = 7200

    # Set var handling for better performance
    env['ANSIBLE_INJECT_FACT_VARS'] = False
    env['ANSIBLE_VARS_PLUGIN_STAGE'] = 'all'
    env['ANSIBLE_GATHER_SUBSET'] = '!all,min'

    if connection == 'local':
        env['ANSIBLE_PYTHON_INTERPRETER'] = sys.executable

    if gathering_policy in ('smart', 'explicit', 'implicit'):
        env['ANSIBLE_GATHERING'] = gathering_policy

    if module_path:
        env['ANSIBLE_LIBRARY'] = ':'.join(
            [env['ANSIBLE_LIBRARY'], module_path]
        )

    get_uid = int(os.getenv('SUDO_UID', os.getuid()))
    try:
        user_pwd = pwd.getpwuid(get_uid)
    except (KeyError, TypeError):
        home = CLOUD_HOME_DIR
    else:
        home = user_pwd.pw_dir

    env['ANSIBLE_LOG_PATH'] = os.path.join(home, 'ansible.log')

    if key:
        env['ANSIBLE_PRIVATE_KEY_FILE'] = key

    # NOTE(cloudnull): Re-apply the original environment ensuring that
    # anything defined on the CLI is set accordingly.
    env.update(os.environ.copy())

    if extra_env_variables:
        if not isinstance(extra_env_variables, dict):
            msg = "extra_env_variables must be a dict"
            LOG.error(msg)
            raise SystemError(msg)
        env.update(extra_env_variables)

    if 'ANSIBLE_CONFIG' not in env and not ansible_cfg:
        ansible_cfg = os.path.join(workdir, 'ansible.cfg')
        config = configparser.ConfigParser()
        if os.path.isfile(ansible_cfg):
            config.read(ansible_cfg)

        if 'defaults' not in config.sections():
            config.add_section('defaults')

        config.set('defaults', 'internal_poll_interval', '0.01')
        with open(ansible_cfg, 'w') as f:
            config.write(f)
        env['ANSIBLE_CONFIG'] = ansible_cfg
    elif 'ANSIBLE_CONFIG' not in env and ansible_cfg:
        env['ANSIBLE_CONFIG'] = ansible_cfg

    command_path = None
    with TempDirs(chdir=False) as ansible_artifact_path:

        r_opts = {
            'private_data_dir': workdir,
            'project_dir': playbook_dir,
            'inventory': _inventory(inventory),
            'envvars': _encode_envvars(env=env),
            'playbook': playbook,
            'verbosity': verbosity,
            'quiet': quiet,
            'extravars': extra_vars,
            'fact_cache': ansible_fact_path,
            'fact_cache_type': 'jsonfile',
            'artifact_dir': ansible_artifact_path,
        }

        if skip_tags:
            r_opts['skip_tags'] = skip_tags

        if tags:
            r_opts['tags'] = tags

        if limit_hosts:
            r_opts['limit'] = limit_hosts

        if parallel_run:
            r_opts['directory_isolation_base_path'] = ansible_artifact_path

        runner_config = ansible_runner.runner_config.RunnerConfig(**r_opts)
        runner_config.prepare()
        runner = ansible_runner.Runner(config=runner_config)

        if reproduce_command:
            command_path = os.path.join(
                workdir,
                "ansible-playbook-command.sh"
            )
            with open(command_path, 'w') as f:
                f.write('#!/usr/bin/env bash\n')
                f.write('echo -e "Exporting environment variables"\n')
                for key, value in r_opts['envvars'].items():
                    f.write('export {}="{}"\n'.format(key, value))
                f.write('echo -e "Running Ansible command"\n')
                args = '{} "$@"\n'.format(' '.join(runner_config.command))
                # Single quote the dict passed to -e
                args = re.sub('({.*})', '\'\\1\'', args)
                f.write(args)
            os.chmod(command_path, 0o750)

        try:
            status, rc = runner.run()
        finally:
            # NOTE(cloudnull): After a playbook executes, ensure the log
            #                  file, if it exists, was created with
            #                  appropriate ownership.
            _log_path = r_opts['envvars']['ANSIBLE_LOG_PATH']
            if os.path.isfile(_log_path):
                os.chown(_log_path, get_uid, -1)
            # Save files we care about
            with open(os.path.join(workdir, 'stdout'), 'w') as f:
                f.write(runner.stdout.read())
            for output in 'status', 'rc':
                val = getattr(runner, output)
                if val:
                    with open(os.path.join(workdir, output), 'w') as f:
                        f.write(str(val))

    if rc != 0:
        if rc == 4 and ignore_unreachable:
            LOG.info('Ignoring unreachable nodes')
        else:
            err_msg = (
                'Ansible execution failed. playbook: {},'
                ' Run Status: {},'
                ' Return Code: {}'.format(
                    playbook,
                    status,
                    rc
                )
            )
            if command_path:
                err_msg += (
                    ', To rerun the failed command manually execute the'
                    ' following script: {}'.format(
                        command_path
                    )
                )

            if not quiet:
                LOG.error(err_msg)

            raise RuntimeError(err_msg)

    LOG.info('Ansible execution success. playbook: %s', playbook)

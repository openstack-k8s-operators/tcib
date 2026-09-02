import io
import os
import tempfile
from unittest import mock

from tcib.client import utils
from tcib.tests import base


class FakeRunnerConfig(object):
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.command = ['ansible-playbook', kwargs['playbook']]
        self.prepare = mock.Mock()
        self.__class__.instances.append(self)


class FakeRunner(object):
    def __init__(self, config):
        self.config = config
        self.stdout = io.StringIO('ok')
        self.status = 'successful'
        self.rc = 0

    def run(self):
        return self.status, self.rc


class TestRunAnsiblePlaybook(base.TestCase):
    def setUp(self):
        super(TestRunAnsiblePlaybook, self).setUp()
        FakeRunnerConfig.instances = []

    @mock.patch.object(utils.ansible_runner, 'Runner', autospec=True)
    @mock.patch.object(
        utils.ansible_runner.runner_config, 'RunnerConfig', autospec=True
    )
    def test_run_ansible_playbook_uses_safe_ssh_defaults(
        self, mock_runner_config, mock_runner
    ):
        mock_runner_config.side_effect = FakeRunnerConfig
        mock_runner.side_effect = FakeRunner

        with tempfile.TemporaryDirectory() as workdir:
            playbook = os.path.join(workdir, 'playbook.yaml')
            with open(playbook, 'w') as f:
                f.write('---\n- hosts: localhost\n  tasks: []\n')

            utils.run_ansible_playbook(
                playbook=playbook,
                inventory='localhost,',
                workdir=workdir,
                playbook_dir=workdir,
                connection='local',
                reproduce_command=False,
            )

        envvars = FakeRunnerConfig.instances[0].kwargs['envvars']
        ssh_args = envvars['ANSIBLE_SSH_ARGS']

        self.assertIn('-o StrictHostKeyChecking=accept-new', ssh_args)
        self.assertNotIn('UserKnownHostsFile', ssh_args)
        self.assertNotIn('ForwardAgent=yes', ssh_args)
        self.assertNotIn('ANSIBLE_HOST_KEY_CHECKING', envvars)

    @mock.patch.object(utils.ansible_runner, 'Runner', autospec=True)
    @mock.patch.object(
        utils.ansible_runner.runner_config, 'RunnerConfig', autospec=True
    )
    def test_run_ansible_playbook_allows_env_overrides(
        self, mock_runner_config, mock_runner
    ):
        mock_runner_config.side_effect = FakeRunnerConfig
        mock_runner.side_effect = FakeRunner

        with tempfile.TemporaryDirectory() as workdir:
            playbook = os.path.join(workdir, 'playbook.yaml')
            with open(playbook, 'w') as f:
                f.write('---\n- hosts: localhost\n  tasks: []\n')

            utils.run_ansible_playbook(
                playbook=playbook,
                inventory='localhost,',
                workdir=workdir,
                playbook_dir=workdir,
                connection='local',
                reproduce_command=False,
                extra_env_variables={
                    'ANSIBLE_SSH_ARGS': '-o ForwardAgent=yes',
                    'ANSIBLE_HOST_KEY_CHECKING': 'False',
                },
            )

        envvars = FakeRunnerConfig.instances[0].kwargs['envvars']
        self.assertEqual(envvars['ANSIBLE_SSH_ARGS'], '-o ForwardAgent=yes')
        self.assertEqual(envvars['ANSIBLE_HOST_KEY_CHECKING'], 'False')

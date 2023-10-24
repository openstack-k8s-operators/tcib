#   Copyright 2016 Red Hat, Inc.
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
import logging
from unittest import mock
import sys

from osc_lib.tests import utils
from tcib.client import container_image as image_build


IMAGE_YAML = """---
container_images:
  - imagename: "test/keystone:tag"
"""

MOCK_WALK = [
    ("/tcib", ["base"], [],),
    ("/tcib/base", ["memcached", "openstack"], ["config.yaml", "test.doc"],),
    ("/tcib/base/memcached", [], ["memcached.yaml"],),
    ("/tcib/base/openstack", ["glance", "keystone", "neutron", "nova"], [],),
    (
        "/tcib/base/openstack/glance",
        [],
        ["glance-registry.yaml", "glance-api.yaml"],
    ),
    ("/tcib/base/openstack/keystone", ["keystone-foo"], ["keystone.yaml"],),
    ("/tcib/base/openstack/keystone/keystone-foo", [], ["keystone-foo.yaml"],),
    ("/tcib/base/openstack/neutron", ["api"], [],),
    ("/tcib/base/openstack/neutron/api", [], ["neutron-api.yml"],),
    ("/tcib/base/openstack/nova", [], [],),
]


class FakeApp(object):
    def __init__(self):
        _stdout = None
        self.LOG = logging.getLogger('FakeApp')
        self.client_manager = None
        self.stdin = sys.stdin
        self.stdout = _stdout or sys.stdout
        self.stderr = sys.stderr
        self.restapi = None
        self.command_options = None
        self.options = FakeOptions()


class FakeOptions(object):
    def __init__(self):
        self.debug = True


class TestContainerImages(utils.TestCommand):
    def setUp(self):
        super(TestContainerImages, self).setUp()
        self.app = FakeApp()
        self.os_walk = mock.patch(
            "os.walk", autospec=True, return_value=iter(MOCK_WALK)
        )
        self.os_walk.start()
        self.addCleanup(self.os_walk.stop)
        self.os_listdir = mock.patch(
            "os.listdir", autospec=True, return_value=["config.yaml"]
        )
        self.os_listdir.start()
        self.addCleanup(self.os_listdir.stop)
        self.run_ansible_playbook = mock.patch(
            "tcib.client.utils.run_ansible_playbook", autospec=True
        )
        self.run_ansible_playbook.start()
        self.addCleanup(self.run_ansible_playbook.stop)
        self.buildah_build_all = mock.patch(
            "tcib.builder.buildah.BuildahBuilder.build_all",
            autospec=True,
        )
        self.mock_buildah = self.buildah_build_all.start()
        self.addCleanup(self.buildah_build_all.stop)
        self.cmd = image_build.Build(self.app, None)

    def _take_action(self, parsed_args):
        self.cmd.image_parents = {"keystone": "foo", "foo": "base"}
        self.cmd.image_levels = {"keystone": 3, "foo": 2, "base": 1}
        mock_open = mock.mock_open(read_data=IMAGE_YAML)
        with mock.patch("os.path.isfile", autospec=True) as mock_isfile:
            mock_isfile.return_value = True
            with mock.patch("os.path.isdir", autospec=True) as mock_isdir:
                mock_isdir.return_value = True
                with mock.patch('builtins.open', mock_open):
                    with mock.patch(
                        "tcib.client.container_image.Build"
                        ".find_image",
                        autospec=True,
                    ) as mock_find_image:
                        mock_find_image.return_value = {"tcib_option": "data"}
                        self.cmd.take_action(parsed_args)

    def test_find_image(self):
        mock_open = mock.mock_open(read_data='---\ntcib_option: "data"')
        with mock.patch('builtins.open', mock_open):
            image = self.cmd.find_image("keystone-foo", "/tcib", "base-image")
        self.assertEqual({"tcib_option": "data"}, image)
        self.assertEqual(
            {
                'keystone-foo': 'keystone',
                'keystone': 'openstack',
                'openstack': 'base',
                'base': 'base-image'
            },
            self.cmd.image_parents
        )
        self.assertEqual(
            {
                'keystone-foo': 4,
                'keystone': 3,
                'openstack': 2,
                'base': 1
            },
            self.cmd.image_levels
        )

    def test_build_tree(self):
        image = self.cmd.build_tree("some/path")
        self.assertEqual(
            image,
            [
                {
                    "base": [
                        "memcached",
                        {
                            "openstack": [
                                "glance",
                                {"keystone": ["keystone-foo"]},
                                {"neutron": ["api"]},
                                "nova",
                            ]
                        },
                    ]
                }
            ],
        )

    def test_image_regex(self):
        image = self.cmd.imagename_to_regex("test/centos-binary-keystone:tag")
        self.assertEqual(image, "keystone")
        image = self.cmd.imagename_to_regex("test/rhel-binary-keystone:tag")
        self.assertEqual(image, "keystone")
        image = self.cmd.imagename_to_regex("test/rhel-source-keystone:tag")
        self.assertEqual(image, "keystone")
        image = self.cmd.imagename_to_regex("test/rhel-rdo-keystone:tag")
        self.assertEqual(image, "keystone")
        image = self.cmd.imagename_to_regex("test/rhel-rhos-keystone:tag")
        self.assertEqual(image, "keystone")
        image = self.cmd.imagename_to_regex("test/other-keystone:tag")
        self.assertEqual(image, "other-keystone")

    def test_rectify_excludes(self):
        self.cmd.identified_images = ["keystone", "nova", "glance"]
        excludes = self.cmd.rectify_excludes(images_to_prepare=["glance"])
        self.assertEqual(excludes, ["keystone", "nova"])

    def test_image_build_yaml(self):
        arglist = ["--config-file", "config.yaml"]
        verifylist = [("config_file", "config.yaml")]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        assert self.mock_buildah.called

    def test_image_build_with_skip_build(self):
        arglist = ["--config-file", "config.yaml", "--skip-build"]
        verifylist = [("config_file", "config.yaml"), ("skip_build", True)]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        assert not self.mock_buildah.called

    def test_image_build_with_push(self):
        arglist = ["--config-file", "config.yaml", "--push"]
        verifylist = [("config_file", "config.yaml"), ("push", True)]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        assert self.mock_buildah.called

    def test_image_build_with_volume(self):
        arglist = ["--config-file", "config.yaml", "--volume", "bind/mount"]
        verifylist = [
            ("config_file", "config.yaml"),
            (
                "volumes",
                [
                    "/etc/pki/rpm-gpg:/etc/pki/rpm-gpg:z",
                    "bind/mount",
                ],
            ),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        # NOTE(dvd): For some reason, in py36, args[0] is a string instead
        # of being a fullblown BuildahBuilder instance. I wasn't able to find
        # the instance anywhere, everything is mocked.
        builder_obj = self.mock_buildah.call_args.args[0]
        if not isinstance(builder_obj, str):
            self.assertIn(
                '/etc/yum.repos.d:/etc/distro.repos.d:z',
                builder_obj.volumes
            )
            self.assertNotIn(
                '/usr/share/tcib/container-images:'
                '/usr/share/tcib/container-images:z',
                builder_obj.volumes
            )

        assert self.mock_buildah.called

    def test_image_build_with_repo_dir(self):
        arglist = ["--repo-dir", "/somewhere"]
        verifylist = [
            ("repo_dir", "/somewhere"),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        builder_obj = self.mock_buildah.call_args.args[0]
        if not isinstance(builder_obj, str):
            self.assertIn(
                '/somewhere:/etc/distro.repos.d:z',
                builder_obj.volumes
            )

        assert self.mock_buildah.called

    def test_image_build_with_exclude(self):
        arglist = ["--exclude", "image1"]
        verifylist = [
            ("excludes", ["image1"]),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        assert self.mock_buildah.called

    def test_image_build_with_no_tcib_package(self):
        arglist = ["--config-file", "config.yaml",
                   "--tcib-extras", "tcib_package="]
        verifylist = [
            ("config_file", "config.yaml"),
            (
                "volumes",
                [
                    "/etc/pki/rpm-gpg:/etc/pki/rpm-gpg:z",
                ],
            ),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)

        # NOTE(dvd): For some reason, in py36, args[0] is a string instead
        # of being a fullblown BuildahBuilder instance. I wasn't able to find
        # the instance anywhere, everything is mocked.
        builder_obj = self.mock_buildah.call_args.args[0]
        if not isinstance(builder_obj, str):
            self.assertIn(
                '/usr/share/tcib/container-images:'
                '/usr/share/tcib/container-images:z',
                builder_obj.volumes
            )

        assert self.mock_buildah.called

    def test_image_build_failure_no_config_file(self):
        arglist = ["--config-file", "not-a-file-config.yaml"]
        verifylist = [
            ("config_file", "not-a-file-config.yaml"),
        ]

        self.check_parser(self.cmd, arglist, verifylist)

    def test_image_build_config_dir(self):
        arglist = ["--config-file", "config.yaml", "--config-path", "/foo"]
        verifylist = [("config_file", "config.yaml"), ("config_path", "/foo")]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        self._take_action(parsed_args=parsed_args)
        self.assertEqual(self.cmd.tcib_config_path, '/foo/tcib')

    def test_image_build_failure_no_config_dir(self):
        arglist = ["--config-path", "not-a-path"]
        verifylist = [
            ("config_path", "not-a-path"),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        with mock.patch("os.path.isfile", autospec=True) as mock_isfile:
            mock_isfile.return_value = True
            self.assertRaises(IOError, self.cmd.take_action, parsed_args)

    def test_process_images(self):
        rtn_value = {'yay': 'values'}
        arglist = ["--config-path", "foobar/"]
        verifylist = [
            ("config_path", "foobar/"),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        expected_images = ['foo', 'foobar']
        image_configs = {}
        self.cmd.tcib_config_path = '/foo/tcib'
        with mock.patch("tcib.client.container_image.Build"
                        ".find_image", autospec=True) as mock_find_image:

            mock_find_image.return_value = rtn_value
            cfgs = self.cmd.process_images(expected_images, parsed_args,
                                           image_configs)
            mock_find_image.assert_called_once_with(
                self.cmd, 'foo', '/foo/tcib', 'centos:stream9')
        self.assertEqual(cfgs, {'foo': rtn_value})


class TestContainerImagesHotfix(utils.TestCommand):
    def setUp(self):
        super(TestContainerImagesHotfix, self).setUp()
        self.app = FakeApp()
        self.run_ansible_playbook = mock.patch(
            "tcib.client.utils.run_ansible_playbook", autospec=True
        )
        self.run_ansible_playbook.start()
        self.addCleanup(self.run_ansible_playbook.stop)
        self.cmd = image_build.HotFix(self.app, None)

    def _take_action(self, parsed_args):
        with mock.patch("os.path.isfile", autospec=True) as mock_isfile:
            mock_isfile.return_value = True
            self.cmd.take_action(parsed_args)

    def test_image_hotfix(self):
        arglist = ["--image", "container1", "--rpms-path", "/opt"]
        verifylist = [
            ("images", ["container1"]),
            ("rpms_path", "/opt"),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self._take_action(parsed_args=parsed_args)

    def test_image_hotfix_multi_image(self):
        arglist = [
            "--image",
            "container1",
            "--image",
            "container2",
            "--rpms-path",
            "/opt",
        ]
        verifylist = [
            ("images", ["container1", "container2"]),
            ("rpms_path", "/opt"),
        ]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        self._take_action(parsed_args=parsed_args)

    def test_image_hotfix_missing_args(self):
        arglist = []
        verifylist = []

        self.assertRaises(
            utils.ParserException,
            self.check_parser,
            self.cmd,
            arglist,
            verifylist,)

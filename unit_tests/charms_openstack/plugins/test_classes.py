import mock
import os
import subprocess

from unit_tests.charms_openstack.charm.utils import BaseOpenStackCharmTest
from unit_tests.utils import patch_open

import charms_openstack.charm.classes as chm
import charms_openstack.plugins.classes as cpl


TEST_CONFIG = {'config': True,
               'openstack-origin': None}


class FakeOpenStackCephConsumingCharm(
        chm.OpenStackCharm,
        cpl.BaseOpenStackCephCharm):
    abstract_class = True


class TestOpenStackCephConsumingCharm(BaseOpenStackCharmTest):

    def setUp(self):
        super(TestOpenStackCephConsumingCharm, self).setUp(
            FakeOpenStackCephConsumingCharm, TEST_CONFIG)

    def test_application_name(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='svc1')
        self.assertEqual(self.target.application_name, 'svc1')

    def test_ceph_service_name(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='charmname')
        self.assertEqual(
            self.target.ceph_service_name,
            'charmname')
        self.target.ceph_service_name_override = 'override'
        self.assertEqual(
            self.target.ceph_service_name,
            'override')

    def test_ceph_key_name(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='charmname')
        self.assertEqual(
            self.target.ceph_key_name,
            'client.charmname')
        self.patch_object(cpl.socket, 'gethostname', return_value='hostname')
        self.target.ceph_key_per_unit_name = True
        self.assertEqual(
            self.target.ceph_key_name,
            'client.charmname.hostname')

    def test_ceph_keyring_path(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='charmname')
        self.assertEqual(
            self.target.ceph_keyring_path,
            '/etc/ceph')
        self.target.snaps = ['gnocchi']
        self.assertEqual(
            self.target.ceph_keyring_path,
            os.path.join(cpl.SNAP_PATH_PREFIX_FORMAT.format('gnocchi'),
                         '/etc/ceph'))

    def test_configure_ceph_keyring(self):
        self.patch_object(cpl.os.path, 'isdir', return_value=False)
        self.patch_object(cpl.ch_core.host, 'mkdir')
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='sarepta')
        self.patch_object(cpl.subprocess, 'check_call')
        self.patch_object(cpl.shutil, 'chown')
        key = 'KEY'
        self.assertEqual(self.target.configure_ceph_keyring(key),
                         '/etc/ceph/ceph.client.sarepta.keyring')
        self.isdir.assert_called_with('/etc/ceph')
        self.mkdir.assert_called_with('/etc/ceph',
                                      owner='root', group='root', perms=0o750)
        self.check_call.assert_called_with([
            'ceph-authtool',
            '/etc/ceph/ceph.client.sarepta.keyring',
            '--create-keyring', '--name=client.sarepta', '--add-key', 'KEY',
            '--mode', '0600',
        ])
        self.target.user = 'ceph'
        self.target.group = 'ceph'
        self.target.configure_ceph_keyring(key)
        self.chown.assert_called_with(
            '/etc/ceph/ceph.client.sarepta.keyring',
            user='ceph', group='ceph')

        self.patch_object(cpl.os, 'chmod')
        self.check_call.side_effect = [
            subprocess.CalledProcessError(42, [], ''), None]
        with self.assertRaises(subprocess.CalledProcessError):
            self.target.configure_ceph_keyring(key)
        self.check_call.reset_mock()
        self.check_call.side_effect = [
            subprocess.CalledProcessError(1, [], ''), None]
        self.target.configure_ceph_keyring(key)
        self.check_call.assert_has_calls([
            mock.call([
                'ceph-authtool',
                '/etc/ceph/ceph.client.sarepta.keyring',
                '--create-keyring', '--name=client.sarepta', '--add-key',
                'KEY', '--mode', '0600']),
            mock.call([
                'ceph-authtool',
                '/etc/ceph/ceph.client.sarepta.keyring',
                '--create-keyring', '--name=client.sarepta', '--add-key',
                'KEY']),
        ])
        self.chmod.assert_called_with('/etc/ceph/ceph.client.sarepta.keyring',
                                      0o600)

    def test_delete_ceph_keyring(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='sarepta')
        self.patch_object(cpl.os, 'remove')
        keyring_filename = '/etc/ceph/ceph.client.sarepta.keyring'
        self.assertEqual(self.target.delete_ceph_keyring(), keyring_filename)
        self.remove.assert_called_once_with(keyring_filename)
        self.remove.side_effect = OSError
        self.assertEqual(self.target.delete_ceph_keyring(), '')


class TestCephCharm(BaseOpenStackCharmTest):

    def setUp(self):
        super(TestCephCharm, self).setUp(cpl.CephCharm, {'source': None})

    def test_ceph_keyring_path(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='charmname')
        self.assertEqual(
            self.target.ceph_keyring_path,
            '/var/lib/ceph/charmname')
        self.target.snaps = ['gnocchi']
        self.assertEqual(
            self.target.ceph_keyring_path,
            os.path.join(cpl.SNAP_PATH_PREFIX_FORMAT.format('gnocchi'),
                         '/var/lib/ceph/charmname'))

    def test_configure_ceph_keyring(self):
        self.patch_object(cpl.os.path, 'isdir', return_value=False)
        self.patch_object(cpl.ch_core.host, 'mkdir')
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='sarepta')
        self.patch_object(cpl.subprocess, 'check_call')
        self.patch_object(cpl.shutil, 'chown')
        self.patch_object(cpl.os, 'symlink')
        key = 'KEY'
        self.patch_object(cpl.os.path, 'exists', return_value=True)
        self.patch_object(cpl.os, 'readlink')
        self.patch_object(cpl.os, 'remove')
        self.readlink.side_effect = OSError
        self.target.configure_ceph_keyring(key)
        self.isdir.assert_called_with('/var/lib/ceph/sarepta')
        self.mkdir.assert_called_with('/var/lib/ceph/sarepta',
                                      owner='root', group='root', perms=0o750)
        self.check_call.assert_called_with([
            'ceph-authtool',
            '/var/lib/ceph/sarepta/ceph.client.sarepta.keyring',
            '--create-keyring', '--name=client.sarepta', '--add-key', 'KEY',
            '--mode', '0600',
        ])
        self.exists.assert_called_with(
            '/etc/ceph/ceph.client.sarepta.keyring')
        self.readlink.assert_called_with(
            '/etc/ceph/ceph.client.sarepta.keyring')
        assert not self.remove.called
        self.symlink.assert_called_with(
            '/var/lib/ceph/sarepta/ceph.client.sarepta.keyring',
            '/etc/ceph/ceph.client.sarepta.keyring')
        self.readlink.side_effect = None
        self.readlink.return_value = '/some/where/else'
        self.target.configure_ceph_keyring(key)
        self.remove.assert_called_with('/etc/ceph/ceph.client.sarepta.keyring')

    def test_delete_ceph_keyring(self):
        self.patch_object(cpl.ch_core.hookenv, 'application_name',
                          return_value='sarepta')
        self.patch_object(cpl.os, 'remove')
        self.target.delete_ceph_keyring()
        self.remove.assert_called_once_with(
            '/var/lib/ceph/sarepta/ceph.client.sarepta.keyring')

    def test_install(self):
        self.patch_object(cpl.subprocess, 'check_output', return_value=b'\n')
        self.patch_target('configure_source')
        self.target.install()
        self.target.configure_source.assert_called()
        self.check_output.assert_called()


class MockCharmForPolicydOverrid(object):

    def __init__(self, *args, **kwargs):
        self._restart_services = False
        self._install = False
        self._upgrade_charm = False
        self._config_changed = False
        self.release = 'mitaka'
        self.policyd_service_name = 'aservice'
        super().__init__(*args, **kwargs)

    def restart_services(self):
        self._restart_services = True

    def install(self):
        self._install = True

    def upgrade_charm(self):
        self._upgrade_charm = True

    def config_changed(self):
        self._config_changed = True


class FakeConsumingPolicydOverride(cpl.PolicydOverridePlugin,
                                   MockCharmForPolicydOverrid):

    pass


class TestPolicydOverridePlugin(BaseOpenStackCharmTest):

    def setUp(self):
        super(TestPolicydOverridePlugin, self).setUp(
            FakeConsumingPolicydOverride, TEST_CONFIG)

    def test__policyd_function_args_no_defines(self):
        args, kwargs = self.target._policyd_function_args()
        self.assertEqual(args, ['mitaka', 'aservice'])
        self.assertEqual(kwargs, {
            'blacklist_paths': None,
            'blacklist_keys': None,
            'template_function': None,
            'restart_handler': None
        })

    def test__policyd_function_args_with_defines(self):
        def my_template_fn(s):
            return "done"

        self.target.policyd_blacklist_paths = ['p1']
        self.target.policyd_blacklist_keys = ['k1']
        self.target.policyd_template_function = my_template_fn
        self.target.policyd_restart_on_change = True
        args, kwargs = self.target._policyd_function_args()
        self.assertEqual(args, ['mitaka', 'aservice'])
        self.assertEqual(kwargs, {
            'blacklist_paths': ['p1'],
            'blacklist_keys': ['k1'],
            'template_function': my_template_fn,
            'restart_handler': self.target.restart_services
        })

    def test__maybe_policyd_overrides(self):
        self.patch_target('_policyd_function_args',
                          return_value=(["args"], {"kwargs": 1}))
        self.patch_object(cpl.ch_policyd,
                          'maybe_do_policyd_overrides',
                          name='mock_policyd_call')
        self.target._maybe_policyd_overrides()
        self.mock_policyd_call.assert_called_once_with(
            "args", kwargs=1)

    def test_install_calls_policyd(self):
        self.patch_target('_maybe_policyd_overrides')
        self.target.install()
        self.assertTrue(self.target._install)
        self._maybe_policyd_overrides.assert_called_once_with()

    def test_upgrade_charm_calls_policyd(self):
        self.patch_target('_maybe_policyd_overrides')
        self.target.upgrade_charm()
        self.assertTrue(self.target._upgrade_charm)
        self._maybe_policyd_overrides.assert_called_once_with()

    def test_config_changed_calls_into_policyd_library(self):
        self.patch_target('_policyd_function_args',
                          return_value=(["args"], {"kwargs": 1}))
        self.patch_object(cpl.ch_policyd,
                          'maybe_do_policyd_overrides_on_config_changed',
                          name='mock_policyd_call')
        self.target.config_changed()
        self.assertTrue(self.target._config_changed)
        self._policyd_function_args.assert_called_once_with()
        self.mock_policyd_call.assert_called_once_with(
            "args", kwargs=1)


class TestTrilioCharmGhostShareAction(BaseOpenStackCharmTest):

    _nfs_shares = "10.20.30.40:/srv/trilioshare"
    _ghost_shares = "50.20.30.40:/srv/trilioshare"

    def setUp(self):
        super().setUp(cpl.TrilioVaultCharm, {})
        self.patch_object(cpl.ch_core.hookenv, "config")
        self.patch_object(cpl.ch_core.host, "mounts")
        self.patch_object(cpl.ch_core.host, "mount")
        self.patch_object(cpl.os.path, "exists")
        self.patch_object(cpl.os, "mkdir")

        self.trilio_charm = cpl.TrilioVaultCharm()
        self._nfs_path = os.path.join(
            cpl.TV_MOUNTS,
            self.trilio_charm._encode_endpoint(self._nfs_shares),
        )
        self._ghost_path = os.path.join(
            cpl.TV_MOUNTS,
            self.trilio_charm._encode_endpoint(self._ghost_shares),
        )

    def test_ghost_share(self):
        self.config.return_value = self._nfs_shares
        self.mounts.return_value = [
            ["/srv/nova", "/dev/sda"],
            [self._nfs_path, self._nfs_shares],
        ]
        self.exists.return_value = False
        self.trilio_charm.ghost_nfs_share(self._ghost_shares)
        self.exists.assert_called_once_with(self._ghost_path)
        self.mkdir.assert_called_once_with(self._ghost_path)
        self.mount.assert_called_once_with(
            self._nfs_path, self._ghost_path, options="bind"
        )

    def test_ghost_share_already_bound(self):
        self.config.return_value = self._nfs_shares
        self.mounts.return_value = [
            ["/srv/nova", "/dev/sda"],
            [self._nfs_path, self._nfs_shares],
            [self._ghost_path, self._nfs_shares],
        ]
        with self.assertRaises(cpl.GhostShareAlreadyMountedException):
            self.trilio_charm.ghost_nfs_share(self._ghost_shares)
        self.mount.assert_not_called()

    def test_ghost_share_nfs_unmounted(self):
        self.config.return_value = self._nfs_shares
        self.mounts.return_value = [["/srv/nova", "/dev/sda"]]
        self.exists.return_value = False
        with self.assertRaises(cpl.NFSShareNotMountedException):
            self.trilio_charm.ghost_nfs_share(self._ghost_shares)
        self.mount.assert_not_called()


class TrilioVaultFoobar(cpl.TrilioVaultCharm):

    abstract_class = True
    name = 'test'
    all_packages = ['foo', 'bar']


class TestTrilioCharmBehaviours(BaseOpenStackCharmTest):

    def setUp(self):
        super().setUp(TrilioVaultFoobar, {})
        self.patch_object(cpl.ch_core.hookenv, "config")
        self.patch_object(cpl.ch_core.hookenv, "status_set")
        self.patch_object(cpl.fetch, "filter_installed_packages")
        self.patch_object(cpl.fetch, "apt_install")
        self.patch_object(cpl.reactive, "is_flag_set")
        self.patch_object(cpl.reactive, "clear_flag")
        self.patch_target('update_api_ports')
        self.patch_target('set_state')
        self.filter_installed_packages.side_effect = lambda p: p

    def test_install(self):
        self.patch_target('configure_source')
        self.is_flag_set.return_value = False

        self.target.install()

        self.is_flag_set.assert_called_with('upgrade.triliovault')
        self.filter_installed_packages.assert_called_once_with(
            self.target.all_packages
        )
        self.apt_install.assert_called_once_with(
            self.target.all_packages,
            fatal=True
        )
        self.clear_flag.assert_not_called()
        self.set_state.assert_called_once_with('test-installed')
        self.update_api_ports.assert_called_once()
        self.configure_source.assert_called_once_with()

    def test_upgrade(self):
        self.patch_target('configure_source')
        self.is_flag_set.return_value = True

        self.target.install()

        self.is_flag_set.assert_called_with('upgrade.triliovault')
        self.filter_installed_packages.assert_not_called()
        self.apt_install.assert_called_once_with(
            self.target.all_packages,
            fatal=True
        )
        self.clear_flag.assert_called_once_with('upgrade.triliovault')
        self.set_state.assert_called_once_with('test-installed')
        self.update_api_ports.assert_called_once()
        self.configure_source.assert_called_once_with()

    def test_configure_source(self):
        self.config.return_value = 'testsource'
        self.patch_object(cpl.charms_openstack.charm.HAOpenStackCharm,
                          'configure_source')
        with patch_open() as (_open, _file):
            self.target.configure_source()
            _open.assert_called_with(
                "/etc/apt/sources.list.d/trilio-gemfury-sources.list",
                "w"
            )
            _file.write.assert_called_once_with('testsource')

    def test_series_upgrade_complete(self):
        self.patch_object(cpl.charms_openstack.charm.HAOpenStackCharm,
                          'series_upgrade_complete')
        self.patch_target('configure_source')
        self.target.series_upgrade_complete()
        self.configure_source.assert_called_once_with()

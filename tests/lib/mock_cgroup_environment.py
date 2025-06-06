# -*- coding: utf-8 -*-
# Copyright 2020 Microsoft Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requires Python 2.6+ and Openssl 1.0+
#
import contextlib
import os
from tests.lib.tools import patch, data_dir
from tests.lib.mock_environment import MockEnvironment, MockCommand

# Mocked commands which are common between v1, v2, and hybrid cgroup environments
_MOCKED_COMMANDS_COMMON = [
   MockCommand(r"^systemctl --version$",
'''systemd 237
+PAM +AUDIT +SELINUX +IMA +APPARMOR +SMACK +SYSVINIT +UTMP +LIBCRYPTSETUP +GCRYPT +GNUTLS +ACL +XZ +LZ4 +SECCOMP +BLKID +ELFUTILS +KMOD -IDN2 +IDN -PCRE2 default-hierarchy=hybrid
'''),

    MockCommand(r"^systemctl show walinuxagent\.service --property ControlGroup$",
'''ControlGroup=/system.slice/walinuxagent.service
'''),

    MockCommand(r"^systemctl show walinuxagent\.service --property Slice",
'''Slice=system.slice
'''),

    MockCommand(r"^systemctl show extension\.service --property ControlGroup$",
'''ControlGroup=/system.slice/extension.service
'''),

    MockCommand(r"^systemctl show (.+) --property CPUQuotaPerSecUSec$",
'''CPUQuotaPerSecUSec=infinity
'''),

    MockCommand(r"^systemctl show (.+) --property CPUAccounting$",
'''CPUAccounting=no
'''),

    MockCommand(r"^systemctl show (.+) --property MemoryAccounting$",
'''MemoryAccounting=no
'''),

    MockCommand(r"^systemctl show (.+) --property LoadState$",
'''LoadState=loaded
'''),

    MockCommand(r"^systemctl set-property (.+) --runtime", ""),

    MockCommand(r"^systemctl stop ([^\s]+)"),

    MockCommand(r"^systemd-run (.+) --unit=([^\s]+) --scope ([^\s]+)",
''' 
Running scope as unit: TEST_UNIT.scope
Thu 28 May 2020 07:25:55 AM PDT
'''),

]

_MOCKED_COMMANDS_V1 = [
    MockCommand(r"^findmnt -t cgroup --noheadings$",
'''/sys/fs/cgroup/systemd          cgroup cgroup rw,nosuid,nodev,noexec,relatime,xattr,name=systemd
/sys/fs/cgroup/devices          cgroup cgroup rw,nosuid,nodev,noexec,relatime,devices
/sys/fs/cgroup/rdma             cgroup cgroup rw,nosuid,nodev,noexec,relatime,rdma
/sys/fs/cgroup/perf_event       cgroup cgroup rw,nosuid,nodev,noexec,relatime,perf_event
/sys/fs/cgroup/net_cls,net_prio cgroup cgroup rw,nosuid,nodev,noexec,relatime,net_cls,net_prio
/sys/fs/cgroup/blkio            cgroup cgroup rw,nosuid,nodev,noexec,relatime,blkio
/sys/fs/cgroup/cpuset           cgroup cgroup rw,nosuid,nodev,noexec,relatime,cpuset
/sys/fs/cgroup/misc             cgroup cgroup rw,nosuid,nodev,noexec,relatime,misc
/sys/fs/cgroup/cpu,cpuacct      cgroup cgroup rw,nosuid,nodev,noexec,relatime,cpu,cpuacct
/sys/fs/cgroup/memory           cgroup cgroup rw,nosuid,nodev,noexec,relatime,memory
/sys/fs/cgroup/freezer          cgroup cgroup rw,nosuid,nodev,noexec,relatime,freezer
/sys/fs/cgroup/hugetlb          cgroup cgroup rw,nosuid,nodev,noexec,relatime,hugetlb
/sys/fs/cgroup/pids             cgroup cgroup rw,nosuid,nodev,noexec,relatime,pids
'''),

    MockCommand(r"^findmnt -t cgroup2 --noheadings$", ''),

    MockCommand(r"^stat -f --format=%T /sys/fs/cgroup$", 'tmpfs'),

]

_MOCKED_COMMANDS_V2 = [
    MockCommand(r"^findmnt -t cgroup2 --noheadings$",
'''/sys/fs/cgroup cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime,nsdelegate,memory_recursiveprot
'''),

    MockCommand(r"^findmnt -t cgroup --noheadings$", ''),

    MockCommand(r"^stat -f --format=%T /sys/fs/cgroup$", 'cgroup2fs'),

]

_MOCKED_COMMANDS_HYBRID = [
    MockCommand(r"^findmnt -t cgroup --noheadings$",
'''/sys/fs/cgroup/systemd          cgroup cgroup rw,nosuid,nodev,noexec,relatime,xattr,name=systemd
/sys/fs/cgroup/devices          cgroup cgroup rw,nosuid,nodev,noexec,relatime,devices
/sys/fs/cgroup/rdma             cgroup cgroup rw,nosuid,nodev,noexec,relatime,rdma
/sys/fs/cgroup/perf_event       cgroup cgroup rw,nosuid,nodev,noexec,relatime,perf_event
/sys/fs/cgroup/net_cls,net_prio cgroup cgroup rw,nosuid,nodev,noexec,relatime,net_cls,net_prio
/sys/fs/cgroup/blkio            cgroup cgroup rw,nosuid,nodev,noexec,relatime,blkio
/sys/fs/cgroup/cpuset           cgroup cgroup rw,nosuid,nodev,noexec,relatime,cpuset
/sys/fs/cgroup/misc             cgroup cgroup rw,nosuid,nodev,noexec,relatime,misc
/sys/fs/cgroup/cpu,cpuacct      cgroup cgroup rw,nosuid,nodev,noexec,relatime,cpu,cpuacct
/sys/fs/cgroup/memory           cgroup cgroup rw,nosuid,nodev,noexec,relatime,memory
/sys/fs/cgroup/freezer          cgroup cgroup rw,nosuid,nodev,noexec,relatime,freezer
/sys/fs/cgroup/hugetlb          cgroup cgroup rw,nosuid,nodev,noexec,relatime,hugetlb
/sys/fs/cgroup/pids             cgroup cgroup rw,nosuid,nodev,noexec,relatime,pids
'''),

    MockCommand(r"^findmnt -t cgroup2 --noheadings$",
'''/sys/fs/cgroup/unified cgroup2 cgroup2 rw,nosuid,nodev,noexec,relatime,nsdelegate
'''),

    MockCommand(r"^stat -f --format=%T /sys/fs/cgroup$", 'tmpfs'),

    MockCommand(r"^stat -f --format=%T /sys/fs/cgroup/unified$", 'cgroup2fs'),

]

_MOCKED_FILES_V1 = [
    ("/proc/self/cgroup", os.path.join(data_dir, 'cgroups', 'v1', 'proc_self_cgroup')),
    (r"/proc/[0-9]+/cgroup", os.path.join(data_dir, 'cgroups', 'v1', 'proc_pid_cgroup')),
    (r"/sys/fs/cgroup/cpu,cpuacct/system.slice/walinuxagent.service/cgroup.procs", os.path.join(data_dir, 'cgroups', 'cgroup.procs')),
    (r"/sys/fs/cgroup/memory/system.slice/walinuxagent.service/cgroup.procs", os.path.join(data_dir, 'cgroups', 'cgroup.procs'))
]

_MOCKED_FILES_V2 = [
    ("/proc/self/cgroup", os.path.join(data_dir, 'cgroups', 'v2', 'proc_self_cgroup')),
    (r"/proc/[0-9]+/cgroup", os.path.join(data_dir, 'cgroups', 'v2', 'proc_pid_cgroup')),
    ("/sys/fs/cgroup/cgroup.subtree_control", os.path.join(data_dir, 'cgroups', 'v2', 'sys_fs_cgroup_cgroup.subtree_control')),
    ("/sys/fs/cgroup/azure.slice/cgroup.subtree_control", os.path.join(data_dir, 'cgroups', 'v2', 'sys_fs_cgroup_cgroup.subtree_control')),
    ("/sys/fs/cgroup/azure.slice/walinuxagent.service/cgroup.subtree_control", os.path.join(data_dir, 'cgroups', 'v2', 'sys_fs_cgroup_cgroup.subtree_control_empty')),
    (r"/sys/fs/cgroup/system.slice/walinuxagent.service/cgroup.procs", os.path.join(data_dir, 'cgroups', 'cgroup.procs'))
]

_MOCKED_FILES_HYBRID = [
    ("/proc/self/cgroup", os.path.join(data_dir, 'cgroups', 'v1', 'proc_self_cgroup')),
    (r"/proc/[0-9]+/cgroup", os.path.join(data_dir, 'cgroups', 'v1', 'proc_pid_cgroup')),
    ("/sys/fs/cgroup/unified/cgroup.controllers", os.path.join(data_dir, 'cgroups', 'hybrid', 'sys_fs_cgroup_cgroup.controllers'))
]

_MOCKED_PATHS = [
    r"^(/lib/systemd/system)",
    r"^(/etc/systemd/system)"
]


class UnitFilePaths:
    walinuxagent = "/lib/systemd/system/walinuxagent.service"
    logcollector = "/lib/systemd/system/azure-walinuxagent-logcollector.slice"
    azure = "/lib/systemd/system/azure.slice"
    vmextensions = "/lib/systemd/system/azure-vmextensions.slice"
    extensionslice = "/lib/systemd/system/azure-vmextensions-Microsoft.CPlat.Extension.slice"
    slice = "/lib/systemd/system/walinuxagent.service.d/10-Slice.conf"
    cpu_accounting = "/lib/systemd/system/walinuxagent.service.d/11-CPUAccounting.conf"
    cpu_quota = "/lib/systemd/system/walinuxagent.service.d/12-CPUQuota.conf"
    memory_accounting = "/lib/systemd/system/walinuxagent.service.d/13-MemoryAccounting.conf"
    extension_service_cpu_accounting = '/lib/systemd/system/extension.service.d/11-CPUAccounting.conf'
    extension_service_cpu_quota = '/lib/systemd/system/extension.service.d/12-CPUQuota.conf'
    extension_service_memory_accounting = '/lib/systemd/system/extension.service.d/13-MemoryAccounting.conf'
    extension_service_memory_limit = '/lib/systemd/system/extension.service.d/14-MemoryLimit.conf'


@contextlib.contextmanager
def mock_cgroup_v1_environment(tmp_dir):
    """
    Creates a mock environment for cgroup v1 hierarchy used by the tests related to cgroups (currently it only
    provides support for systemd platforms).
    The command output used in __MOCKED_COMMANDS comes from an Ubuntu 20 system.
    """
    data_files = [
        (os.path.join(data_dir, 'init', 'walinuxagent.service'), UnitFilePaths.walinuxagent),
        (os.path.join(data_dir, 'init', 'azure.slice'), UnitFilePaths.azure),
        (os.path.join(data_dir, 'init', 'azure-vmextensions.slice'), UnitFilePaths.vmextensions)
    ]

    with patch('azurelinuxagent.ga.cgroupapi.CGroupUtil.distro_supported', return_value=True):
        with patch('azurelinuxagent.common.osutil.systemd.is_systemd', return_value=True):
            with patch('azurelinuxagent.common.conf.get_cgroup_disable_on_process_check_failure', return_value=False):
                with MockEnvironment(tmp_dir, commands=_MOCKED_COMMANDS_COMMON + _MOCKED_COMMANDS_V1, paths=_MOCKED_PATHS, files=_MOCKED_FILES_V1, data_files=data_files) as mock:
                    yield mock


@contextlib.contextmanager
def mock_cgroup_v2_environment(tmp_dir):
    """
    Creates a mock environment for cgroup v2 hierarchy used by the tests related to cgroups (currently it only
    provides support for systemd platforms).
    The command output used in __MOCKED_COMMANDS comes from an Ubuntu 22 system.
    """
    data_files = [
        (os.path.join(data_dir, 'init', 'walinuxagent.service'), UnitFilePaths.walinuxagent),
        (os.path.join(data_dir, 'init', 'azure.slice'), UnitFilePaths.azure),
        (os.path.join(data_dir, 'init', 'azure-vmextensions.slice'), UnitFilePaths.vmextensions)
    ]

    with patch('azurelinuxagent.ga.cgroupapi.CGroupUtil.distro_supported', return_value=True):
        with patch('azurelinuxagent.common.osutil.systemd.is_systemd', return_value=True):
            with patch('azurelinuxagent.common.conf.get_cgroup_disable_on_process_check_failure', return_value=False):
                with MockEnvironment(tmp_dir, commands=_MOCKED_COMMANDS_COMMON + _MOCKED_COMMANDS_V2, paths=_MOCKED_PATHS, files=_MOCKED_FILES_V2, data_files=data_files) as mock:
                    yield mock


@contextlib.contextmanager
def mock_cgroup_hybrid_environment(tmp_dir):
    """
    Creates a mock environment for cgroup hybrid hierarchy used by the tests related to cgroups (currently it only
    provides support for systemd platforms).
    """
    data_files = [
        (os.path.join(data_dir, 'init', 'walinuxagent.service'), UnitFilePaths.walinuxagent),
        (os.path.join(data_dir, 'init', 'azure.slice'), UnitFilePaths.azure),
        (os.path.join(data_dir, 'init', 'azure-vmextensions.slice'), UnitFilePaths.vmextensions)
    ]

    with patch('azurelinuxagent.ga.cgroupapi.CGroupUtil.distro_supported', return_value=True):
        with patch('azurelinuxagent.common.osutil.systemd.is_systemd', return_value=True):
            with patch('azurelinuxagent.common.conf.get_cgroup_disable_on_process_check_failure', return_value=False):
                with MockEnvironment(tmp_dir, commands=_MOCKED_COMMANDS_COMMON + _MOCKED_COMMANDS_HYBRID, paths=_MOCKED_PATHS, files=_MOCKED_FILES_HYBRID, data_files=data_files) as mock:
                    yield mock

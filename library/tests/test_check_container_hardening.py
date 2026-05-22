# Copyright 2024-2025 NetCracker Technology Corporation
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

"""Unit tests for PlatformLibrary.check_container_hardening (CH1–CH12)."""

from unittest.mock import Mock, patch

_UNSET = object()  # sentinel: "caller did not provide a value" vs explicit None

import pytest
from integration_library_builtIn.PlatformLibrary import PlatformLibrary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def library():
    """Minimal PlatformLibrary instance with all Kubernetes calls stubbed out."""
    with patch('integration_library_builtIn.PlatformLibrary.get_kubernetes_api_client') as mock_get_client, \
         patch('integration_library_builtIn.PlatformLibrary.KubernetesClient') as mock_k8s_cls, \
         patch('integration_library_builtIn.PlatformLibrary.OpenShiftClient'):
        mock_k8s_cls.return_value.k8s_apps_v1_client = Mock()
        mock_get_client.return_value = Mock()
        lib = PlatformLibrary()
        lib.k8s_core_v1_client = Mock()
        yield lib


# ---------------------------------------------------------------------------
# Pod / container builder helpers
# ---------------------------------------------------------------------------

def _make_seccomp(profile_type='RuntimeDefault'):
    sc = Mock()
    sc.type = profile_type
    return sc


def _make_capabilities(drop=('ALL',), add=None):
    caps = Mock()
    caps.drop = list(drop)
    caps.add = list(add) if add else None
    return caps


def _make_container_sc(
    run_as_non_root=True,
    run_as_user=1001,
    privileged=False,
    allow_privilege_escalation=False,
    read_only_root_filesystem=True,
    capabilities=None,
    seccomp_profile=None,
):
    csc = Mock()
    csc.run_as_non_root = run_as_non_root
    csc.run_as_user = run_as_user
    csc.privileged = privileged
    csc.allow_privilege_escalation = allow_privilege_escalation
    csc.read_only_root_filesystem = read_only_root_filesystem
    csc.capabilities = capabilities if capabilities is not None else _make_capabilities()
    csc.seccomp_profile = seccomp_profile
    return csc


def _make_pod_sc(
    run_as_non_root=True,
    run_as_user=1001,
    seccomp_profile=_UNSET,
):
    psc = Mock()
    psc.run_as_non_root = run_as_non_root
    psc.run_as_user = run_as_user
    psc.seccomp_profile = _make_seccomp() if seccomp_profile is _UNSET else seccomp_profile
    return psc


def _make_volume(name='data', host_path=None):
    vol = Mock()
    vol.name = name
    vol.host_path = host_path
    return vol


def _make_host_path_volume(name='host-data', path='/var/lib'):
    hp = Mock()
    hp.path = path
    vol = Mock()
    vol.name = name
    vol.host_path = hp
    return vol


def _make_volume_mount(name='tmp', mount_path='/tmp', mount_propagation=None):
    vm = Mock()
    vm.name = name
    vm.mount_path = mount_path
    vm.mount_propagation = mount_propagation
    return vm


def _make_port(container_port):
    p = Mock()
    p.container_port = container_port
    return p


def _make_env_secret(name='PASSWORD'):
    env = Mock()
    env.name = name
    env.value_from = Mock()
    env.value_from.secret_key_ref = Mock()
    return env


def _make_env_plain(name='FOO', value='bar'):
    env = Mock()
    env.name = name
    env.value_from = None
    return env


def _make_env_from_secret(secret_name='my-secret'):
    ef = Mock()
    ef.secret_ref = Mock()
    ef.secret_ref.name = secret_name
    return ef


def _make_container(
    name='app',
    image='my-app:1.0.0',
    security_context=_UNSET,
    volume_mounts=None,
    ports=None,
    env=None,
    env_from=None,
):
    c = Mock()
    c.name = name
    c.image = image
    c.security_context = _make_container_sc() if security_context is _UNSET else security_context
    c.volume_mounts = volume_mounts or []
    c.ports = ports or []
    c.env = env or []
    c.env_from = env_from or []
    return c


def _make_pod(
    name='pod-0',
    labels=None,
    pod_sc=None,
    containers=None,
    init_containers=None,
    host_pid=False,
    host_ipc=False,
    host_network=False,
    volumes=None,
):
    """Build a Mock pod that is fully compliant by default."""
    pod = Mock()
    pod.metadata.name = name
    pod.metadata.labels = labels if labels is not None else {
        'app.kubernetes.io/part-of': 'kafka',
        'app.kubernetes.io/name': 'kafka',
    }

    spec = Mock()
    spec.host_pid = host_pid
    spec.host_ipc = host_ipc
    spec.host_network = host_network
    spec.volumes = volumes or [_make_volume()]
    spec.init_containers = init_containers or []
    spec.containers = containers if containers is not None else [_make_container()]
    spec.security_context = pod_sc if pod_sc is not None else _make_pod_sc()

    pod.spec = spec
    return pod


# ---------------------------------------------------------------------------
# _check_pod_hardening_rules — per-rule violation tests
# ---------------------------------------------------------------------------

class TestCheckPodHardeningRules:

    def _check(self, pod, excluded=None):
        lib = PlatformLibrary.__new__(PlatformLibrary)
        return lib._check_pod_hardening_rules(pod, excluded or set())

    # --- CH1 ----------------------------------------------------------------

    def test_ch1_pass_run_as_non_root_on_pod(self):
        pod = _make_pod(pod_sc=_make_pod_sc(run_as_non_root=True, run_as_user=1001))
        assert not any('[CH1]' in v for v in self._check(pod))

    def test_ch1_fail_run_as_non_root_false(self):
        container = _make_container(security_context=_make_container_sc(run_as_non_root=False))
        pod = _make_pod(
            pod_sc=_make_pod_sc(run_as_non_root=False),
            containers=[container],
        )
        violations = self._check(pod)
        assert any('[CH1]' in v and 'runAsNonRoot' in v for v in violations)

    def test_ch1_fail_run_as_user_zero(self):
        container = _make_container(security_context=_make_container_sc(run_as_user=0))
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH1]' in v and 'runAsUser=0' in v for v in violations)

    def test_ch1_pass_when_excluded(self):
        container = _make_container(security_context=_make_container_sc(run_as_non_root=False))
        pod = _make_pod(pod_sc=_make_pod_sc(run_as_non_root=False), containers=[container])
        violations = self._check(pod, excluded={'CH1'})
        assert not any('[CH1]' in v for v in violations)

    # --- CH2 ----------------------------------------------------------------

    def test_ch2_pass_privilege_escalation_false(self):
        pod = _make_pod()
        assert not any('[CH2]' in v for v in self._check(pod))

    def test_ch2_fail_privileged_true(self):
        container = _make_container(
            security_context=_make_container_sc(privileged=True, allow_privilege_escalation=False)
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH2]' in v and 'privileged=true' in v for v in violations)

    def test_ch2_fail_allow_privilege_escalation_not_false(self):
        container = _make_container(
            security_context=_make_container_sc(allow_privilege_escalation=None)
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH2]' in v and 'allowPrivilegeEscalation' in v for v in violations)

    def test_ch2_pass_when_excluded(self):
        container = _make_container(
            security_context=_make_container_sc(privileged=True, allow_privilege_escalation=True)
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH2'})
        assert not any('[CH2]' in v for v in violations)

    # --- CH3 ----------------------------------------------------------------

    def test_ch3_pass_no_host_namespaces(self):
        pod = _make_pod(host_pid=False, host_ipc=False, host_network=False)
        assert not any('[CH3]' in v for v in self._check(pod))

    def test_ch3_fail_host_pid(self):
        pod = _make_pod(host_pid=True)
        assert any('[CH3]' in v and 'hostPID' in v for v in self._check(pod))

    def test_ch3_fail_host_ipc(self):
        pod = _make_pod(host_ipc=True)
        assert any('[CH3]' in v and 'hostIPC' in v for v in self._check(pod))

    def test_ch3_fail_host_network(self):
        pod = _make_pod(host_network=True)
        assert any('[CH3]' in v and 'hostNetwork' in v for v in self._check(pod))

    def test_ch3_pass_when_excluded(self):
        pod = _make_pod(host_pid=True, host_ipc=True, host_network=True)
        violations = self._check(pod, excluded={'CH3', 'CH10'})
        assert not any('[CH3]' in v for v in violations)

    # --- CH4 ----------------------------------------------------------------

    def test_ch4_pass_read_only_root_filesystem(self):
        pod = _make_pod()
        assert not any('[CH4]' in v for v in self._check(pod))

    def test_ch4_fail_read_only_root_filesystem_false(self):
        container = _make_container(
            security_context=_make_container_sc(read_only_root_filesystem=False)
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH4]' in v for v in violations)

    def test_ch4_fail_no_security_context(self):
        container = _make_container(security_context=None)
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH4]' in v for v in violations)

    def test_ch4_pass_when_excluded(self):
        container = _make_container(
            security_context=_make_container_sc(read_only_root_filesystem=False)
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH4'})
        assert not any('[CH4]' in v for v in violations)

    # --- CH5 ----------------------------------------------------------------

    def test_ch5_pass_drop_all(self):
        pod = _make_pod()
        assert not any('[CH5]' in v for v in self._check(pod))

    def test_ch5_fail_no_capabilities_block(self):
        csc = _make_container_sc()
        csc.capabilities = None
        container = _make_container(security_context=csc)
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH5]' in v and 'no capabilities block' in v for v in violations)

    def test_ch5_fail_drop_does_not_contain_all(self):
        container = _make_container(
            security_context=_make_container_sc(capabilities=_make_capabilities(drop=['NET_ADMIN']))
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH5]' in v and "does not contain" in v for v in violations)

    def test_ch5_fail_capabilities_add_present(self):
        container = _make_container(
            security_context=_make_container_sc(
                capabilities=_make_capabilities(drop=['ALL'], add=['NET_ADMIN'])
            )
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH5]' in v and 'capabilities.add' in v for v in violations)

    def test_ch5_pass_drop_all_uppercase(self):
        container = _make_container(
            security_context=_make_container_sc(capabilities=_make_capabilities(drop=['ALL']))
        )
        pod = _make_pod(containers=[container])
        assert not any('[CH5]' in v for v in self._check(pod))

    def test_ch5_pass_when_excluded(self):
        csc = _make_container_sc()
        csc.capabilities = None
        container = _make_container(security_context=csc)
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH5'})
        assert not any('[CH5]' in v for v in violations)

    # --- CH6 ----------------------------------------------------------------

    def test_ch6_pass_seccomp_runtime_default_on_pod(self):
        pod = _make_pod(pod_sc=_make_pod_sc(seccomp_profile=_make_seccomp('RuntimeDefault')))
        assert not any('[CH6]' in v for v in self._check(pod))

    def test_ch6_pass_seccomp_runtime_default_on_container(self):
        container = _make_container(
            security_context=_make_container_sc(seccomp_profile=_make_seccomp('RuntimeDefault'))
        )
        pod = _make_pod(containers=[container])
        assert not any('[CH6]' in v for v in self._check(pod))

    def test_ch6_fail_seccomp_unconfined(self):
        container = _make_container(
            security_context=_make_container_sc(seccomp_profile=_make_seccomp('Unconfined'))
        )
        pod = _make_pod(
            pod_sc=_make_pod_sc(seccomp_profile=None),
            containers=[container],
        )
        violations = self._check(pod)
        assert any('[CH6]' in v and 'Unconfined' in v for v in violations)

    def test_ch6_fail_seccomp_not_set(self):
        container = _make_container(
            security_context=_make_container_sc(seccomp_profile=None)
        )
        psc = _make_pod_sc(seccomp_profile=None)
        pod = _make_pod(pod_sc=psc, containers=[container])
        violations = self._check(pod)
        assert any('[CH6]' in v and 'not set' in v for v in violations)

    def test_ch6_pass_when_excluded(self):
        container = _make_container(
            security_context=_make_container_sc(seccomp_profile=_make_seccomp('Unconfined'))
        )
        pod = _make_pod(pod_sc=_make_pod_sc(seccomp_profile=None), containers=[container])
        violations = self._check(pod, excluded={'CH6'})
        assert not any('[CH6]' in v for v in violations)

    # --- CH7 ----------------------------------------------------------------

    def test_ch7_pass_no_bidirectional_mount(self):
        container = _make_container(
            volume_mounts=[_make_volume_mount(mount_propagation=None)]
        )
        pod = _make_pod(containers=[container])
        assert not any('[CH7]' in v for v in self._check(pod))

    def test_ch7_fail_bidirectional_mount(self):
        container = _make_container(
            volume_mounts=[_make_volume_mount(name='data', mount_path='/data',
                                              mount_propagation='Bidirectional')]
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH7]' in v and 'Bidirectional' in v for v in violations)

    def test_ch7_pass_when_excluded(self):
        container = _make_container(
            volume_mounts=[_make_volume_mount(mount_propagation='Bidirectional')]
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH7'})
        assert not any('[CH7]' in v for v in violations)

    # --- CH8 ----------------------------------------------------------------

    def test_ch8_pass_safe_port(self):
        container = _make_container(ports=[_make_port(9092)])
        pod = _make_pod(containers=[container])
        assert not any('[CH8]' in v for v in self._check(pod))

    def test_ch8_fail_forbidden_port_22(self):
        container = _make_container(ports=[_make_port(22)])
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH8]' in v and '22' in v for v in violations)

    def test_ch8_fail_forbidden_port_1080(self):
        container = _make_container(ports=[_make_port(1080)])
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH8]' in v and '1080' in v for v in violations)

    def test_ch8_pass_when_excluded(self):
        container = _make_container(ports=[_make_port(22)])
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH8'})
        assert not any('[CH8]' in v for v in violations)

    # --- CH9 ----------------------------------------------------------------

    def test_ch9_pass_image_with_tag(self):
        container = _make_container(image='my-app:1.2.3')
        pod = _make_pod(containers=[container])
        assert not any('[CH9]' in v for v in self._check(pod))

    def test_ch9_pass_image_with_latest_tag(self):
        container = _make_container(image='my-app:latest')
        pod = _make_pod(containers=[container])
        assert not any('[CH9]' in v for v in self._check(pod))

    def test_ch9_fail_image_without_tag(self):
        container = _make_container(image='my-app')
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH9]' in v and 'no tag' in v for v in violations)

    def test_ch9_pass_when_excluded(self):
        container = _make_container(image='my-app')
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH9'})
        assert not any('[CH9]' in v for v in violations)

    # --- CH10 ---------------------------------------------------------------

    def test_ch10_pass_no_host_network(self):
        pod = _make_pod(host_network=False)
        assert not any('[CH10]' in v for v in self._check(pod))

    def test_ch10_fail_host_network_true(self):
        pod = _make_pod(host_network=True)
        violations = self._check(pod)
        assert any('[CH10]' in v for v in violations)

    def test_ch10_pass_when_excluded(self):
        pod = _make_pod(host_network=True)
        violations = self._check(pod, excluded={'CH3', 'CH10'})
        assert not any('[CH10]' in v for v in violations)

    # --- CH11 ---------------------------------------------------------------

    def test_ch11_pass_no_host_path(self):
        pod = _make_pod(volumes=[_make_volume(name='data', host_path=None)])
        assert not any('[CH11]' in v for v in self._check(pod))

    def test_ch11_fail_host_path_volume(self):
        pod = _make_pod(volumes=[_make_host_path_volume(name='host-data', path='/var/lib')])
        violations = self._check(pod)
        assert any('[CH11]' in v and 'hostPath' in v for v in violations)

    def test_ch11_pass_when_excluded(self):
        pod = _make_pod(volumes=[_make_host_path_volume()])
        violations = self._check(pod, excluded={'CH11'})
        assert not any('[CH11]' in v for v in violations)

    # --- CH12 ---------------------------------------------------------------

    def test_ch12_pass_no_secret_env(self):
        container = _make_container(env=[_make_env_plain()], env_from=[])
        pod = _make_pod(containers=[container])
        assert not any('[CH12]' in v for v in self._check(pod))

    def test_ch12_fail_secret_key_ref_in_env(self):
        container = _make_container(env=[_make_env_secret('DB_PASSWORD')])
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH12]' in v and 'secretKeyRef' in v for v in violations)

    def test_ch12_fail_secret_ref_in_env_from(self):
        container = _make_container(env_from=[_make_env_from_secret('app-secret')])
        pod = _make_pod(containers=[container])
        violations = self._check(pod)
        assert any('[CH12]' in v and 'secretRef' in v and 'app-secret' in v for v in violations)

    def test_ch12_pass_when_excluded(self):
        container = _make_container(
            env=[_make_env_secret()],
            env_from=[_make_env_from_secret()],
        )
        pod = _make_pod(containers=[container])
        violations = self._check(pod, excluded={'CH12'})
        assert not any('[CH12]' in v for v in violations)

    # --- Init containers are also checked -----------------------------------

    def test_init_container_violation_is_reported(self):
        init_container = _make_container(
            name='init-app',
            image='busybox',  # no tag
        )
        pod = _make_pod(init_containers=[init_container])
        violations = self._check(pod)
        assert any('[CH9]' in v and 'init-app' in v for v in violations)

    # --- Fully compliant pod has no violations ------------------------------

    def test_fully_compliant_pod_has_no_violations(self):
        pod = _make_pod()
        assert self._check(pod) == []


# ---------------------------------------------------------------------------
# check_container_hardening — integration-level tests
# ---------------------------------------------------------------------------

class TestCheckContainerHardening:

    def _make_library_with_pods(self, pods):
        with patch('integration_library_builtIn.PlatformLibrary.get_kubernetes_api_client'), \
             patch('integration_library_builtIn.PlatformLibrary.KubernetesClient') as kc, \
             patch('integration_library_builtIn.PlatformLibrary.OpenShiftClient'):
            kc.return_value.k8s_apps_v1_client = Mock()
            lib = PlatformLibrary()
            lib.k8s_core_v1_client = Mock()
            lib.get_pods = Mock(return_value=pods)
            return lib

    def test_passes_when_all_pods_compliant(self):
        pod = _make_pod()
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening('kafka', namespace='ns')

    def test_raises_on_violation(self):
        container = _make_container(image='my-app')  # no tag → CH9
        pod = _make_pod(containers=[container])
        lib = self._make_library_with_pods([pod])
        with pytest.raises(AssertionError, match='CH9'):
            lib.check_container_hardening('kafka', namespace='ns')

    def test_filters_by_part_of_label(self):
        """Only pods whose app.kubernetes.io/part-of matches are checked."""
        bad_container = _make_container(image='untagged')  # CH9
        other_pod = _make_pod(
            name='other-pod',
            labels={'app.kubernetes.io/part-of': 'different-service'},
            containers=[bad_container],
        )
        good_pod = _make_pod(name='kafka-0')
        lib = self._make_library_with_pods([other_pod, good_pod])
        # Should not raise — bad pod is in a different part-of
        lib.check_container_hardening('kafka', namespace='ns')

    def test_accepts_part_of_as_string(self):
        pod = _make_pod()
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening('kafka', namespace='ns')  # string, not list

    def test_accepts_part_of_as_list(self):
        pod = _make_pod()
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening(['kafka', 'kafka-services'], namespace='ns')

    def test_multiple_part_of_values_all_checked(self):
        bad = _make_container(image='untagged')
        pod_a = _make_pod(
            name='pod-a',
            labels={'app.kubernetes.io/part-of': 'kafka',
                    'app.kubernetes.io/name': 'kafka'},
            containers=[bad],
        )
        pod_b = _make_pod(
            name='pod-b',
            labels={'app.kubernetes.io/part-of': 'kafka-services',
                    'app.kubernetes.io/name': 'kafka-services'},
            containers=[bad],
        )
        lib = self._make_library_with_pods([pod_a, pod_b])
        with pytest.raises(AssertionError) as exc_info:
            lib.check_container_hardening(['kafka', 'kafka-services'], namespace='ns')
        msg = str(exc_info.value)
        assert 'pod-a' in msg
        assert 'pod-b' in msg

    def test_no_matching_pods_does_not_raise(self):
        """Zero matching pods should log a warning but not raise."""
        pod = _make_pod(labels={'app.kubernetes.io/part-of': 'other'})
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening('kafka', namespace='ns')

    def test_exclusion_suppresses_rule_for_named_app(self):
        """CH12 excluded for cruise-control should not produce a violation."""
        container = _make_container(env=[_make_env_secret()])
        pod = _make_pod(
            labels={
                'app.kubernetes.io/part-of': 'kafka',
                'app.kubernetes.io/name': 'kafka-cruise-control',
            },
            containers=[container],
        )
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening(
            'kafka',
            namespace='ns',
            exclusions={'kafka-cruise-control': 'CH12'},
        )

    def test_exclusion_does_not_suppress_other_rules(self):
        """Excluding CH12 must not hide a CH9 violation on the same pod."""
        container = _make_container(
            image='untagged',  # CH9
            env=[_make_env_secret()],  # CH12
        )
        pod = _make_pod(
            labels={
                'app.kubernetes.io/part-of': 'kafka',
                'app.kubernetes.io/name': 'kafka-cruise-control',
            },
            containers=[container],
        )
        lib = self._make_library_with_pods([pod])
        with pytest.raises(AssertionError, match='CH9'):
            lib.check_container_hardening(
                'kafka',
                namespace='ns',
                exclusions={'kafka-cruise-control': 'CH12'},
            )

    def test_exclusion_multiple_rules_comma_separated(self):
        """Comma-separated list like 'CH1,CH10' should exclude both rules."""
        container = _make_container(security_context=_make_container_sc(run_as_non_root=False))
        pod = _make_pod(
            pod_sc=_make_pod_sc(run_as_non_root=False),
            host_network=True,
            labels={
                'app.kubernetes.io/part-of': 'kafka',
                'app.kubernetes.io/name': 'some-daemon',
            },
            containers=[container],
        )
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening(
            'kafka',
            namespace='ns',
            exclusions={'some-daemon': 'CH1,CH3,CH10'},
        )

    def test_violation_message_contains_pod_name_and_rule(self):
        container = _make_container(image='my-app')
        pod = _make_pod(name='kafka-broker-0', containers=[container])
        lib = self._make_library_with_pods([pod])
        with pytest.raises(AssertionError) as exc_info:
            lib.check_container_hardening('kafka', namespace='ns')
        assert 'kafka-broker-0' in str(exc_info.value)
        assert 'CH9' in str(exc_info.value)

    def test_multiple_violations_all_reported(self):
        """All violations across all pods should appear in the error message."""
        c1 = _make_container(name='c1', image='untagged')  # CH9
        p1 = _make_pod(name='pod-1', containers=[c1])

        c2 = _make_container(name='c2', security_context=_make_container_sc(privileged=True))
        p2 = _make_pod(name='pod-2', containers=[c2])

        lib = self._make_library_with_pods([p1, p2])
        with pytest.raises(AssertionError) as exc_info:
            lib.check_container_hardening('kafka', namespace='ns')
        msg = str(exc_info.value)
        assert 'pod-1' in msg
        assert 'pod-2' in msg

    def test_namespace_passed_to_get_pods(self):
        lib = self._make_library_with_pods([])
        lib.check_container_hardening('kafka', namespace='my-ns')
        lib.get_pods.assert_called_once_with('my-ns')

    # --- _all global exclusions ---------------------------------------------

    def test_all_exclusion_suppresses_rule_for_every_pod(self):
        """_all key skips the rule on all pods regardless of their app name."""
        c1 = _make_container(image='untagged')  # CH9
        p1 = _make_pod(name='pod-1', labels={'app.kubernetes.io/part-of': 'kafka',
                                              'app.kubernetes.io/name': 'kafka'}, containers=[c1])
        c2 = _make_container(image='also-untagged')  # CH9
        p2 = _make_pod(name='pod-2', labels={'app.kubernetes.io/part-of': 'kafka',
                                              'app.kubernetes.io/name': 'other-app'}, containers=[c2])
        lib = self._make_library_with_pods([p1, p2])
        lib.check_container_hardening('kafka', namespace='ns', exclusions={'_all': 'CH9'})

    def test_all_exclusion_combined_with_per_app_exclusion(self):
        """_all and per-app exclusions are merged; both take effect."""
        secret_container = _make_container(
            image='untagged',          # CH9 — covered by _all
            env=[_make_env_secret()],  # CH12 — covered by per-app
        )
        pod = _make_pod(
            labels={'app.kubernetes.io/part-of': 'kafka',
                    'app.kubernetes.io/name': 'my-app'},
            containers=[secret_container],
        )
        lib = self._make_library_with_pods([pod])
        lib.check_container_hardening(
            'kafka', namespace='ns',
            exclusions={'_all': 'CH9', 'my-app': 'CH12'},
        )

    def test_all_exclusion_does_not_suppress_unlisted_rules(self):
        """_all=CH9 must not hide a CH2 violation on the same pod."""
        container = _make_container(
            image='untagged',          # CH9 — excluded via _all
            security_context=_make_container_sc(privileged=True),  # CH2 — not excluded
        )
        pod = _make_pod(containers=[container])
        lib = self._make_library_with_pods([pod])
        with pytest.raises(AssertionError, match='CH2'):
            lib.check_container_hardening('kafka', namespace='ns', exclusions={'_all': 'CH9'})

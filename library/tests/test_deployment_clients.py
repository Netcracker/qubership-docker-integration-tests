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

"""Tests for KubernetesClient and OpenShiftClient, the deployment helpers behind PlatformLibrary.

The AppsV1Api is mocked, but deployments and scales are real kubernetes client models, so a client
update that renames or retypes model attributes fails here. The two clients classify active and
inactive deployments differently; the tests pin the current behavior of each.
"""

from unittest.mock import patch

import KubernetesClient as kubernetes_client_module
import OpenShiftClient as openshift_client_module
import pytest
from kubernetes.client import (
    V1Deployment,
    V1DeploymentSpec,
    V1DeploymentStatus,
    V1LabelSelector,
    V1ObjectMeta,
    V1PodTemplateSpec,
    V1Scale,
    V1ScaleSpec,
    V1ScaleStatus,
)

NAMESPACE = "kafka"


def deployment(name, service="kafka", replicas=None, available=None, unavailable=None):
    labels = {"clusterName": service, "name": name}
    return V1Deployment(
        metadata=V1ObjectMeta(name=name),
        spec=V1DeploymentSpec(
            selector=V1LabelSelector(match_labels={"name": name}),
            template=V1PodTemplateSpec(metadata=V1ObjectMeta(labels=labels)),
        ),
        status=V1DeploymentStatus(replicas=replicas, available_replicas=available, unavailable_replicas=unavailable),
    )


DEPLOYMENTS = [
    deployment("kafka-ready", replicas=2, available=2),
    deployment("kafka-degraded", replicas=2, available=1, unavailable=1),
    deployment("kafka-scaled-down"),
    deployment("zookeeper", service="zookeeper", replicas=1, available=1),
]


def make_client(module, class_name):
    with patch.object(module.client, "AppsV1Api") as apps_v1_api:
        instance = getattr(module, class_name)(api_client=None)
    apps = apps_v1_api.return_value
    apps.list_namespaced_deployment.return_value.items = DEPLOYMENTS
    apps.read_namespaced_deployment.side_effect = lambda name, namespace: next(
        d for d in DEPLOYMENTS if d.metadata.name == name
    )
    return instance, apps


@pytest.fixture(
    params=[(kubernetes_client_module, "KubernetesClient"), (openshift_client_module, "OpenShiftClient")],
    ids=["kubernetes", "openshift"],
)
def any_client(request):
    return make_client(*request.param)


@pytest.fixture
def kubernetes_client():
    return make_client(kubernetes_client_module, "KubernetesClient")[0]


@pytest.fixture
def openshift_client():
    return make_client(openshift_client_module, "OpenShiftClient")[0]


class TestCommonBehavior:
    def test_deployment_names_for_service(self, any_client):
        client, apps = any_client

        assert client.get_deployment_entity_names_for_service(NAMESPACE, "kafka") == [
            "kafka-ready",
            "kafka-degraded",
            "kafka-scaled-down",
        ]
        assert client.get_deployment_entities_count_for_service(NAMESPACE, "kafka") == 3
        apps.list_namespaced_deployment.assert_called_with(NAMESPACE)

    def test_deployment_names_by_custom_label(self, any_client):
        client, _ = any_client

        assert client.get_deployment_entity_names_for_service(NAMESPACE, "zookeeper", label="name") == ["zookeeper"]

    def test_first_deployment_name_for_service(self, any_client):
        client, _ = any_client

        assert client.get_first_deployment_entity_name_for_service(NAMESPACE, "zookeeper") == "zookeeper"
        assert client.get_first_deployment_entity_name_for_service(NAMESPACE, "missing") is None

    def test_pod_selector_labels(self, any_client):
        client, _ = any_client

        assert client.get_deployment_entity_pod_selector_labels("kafka-ready", NAMESPACE) == {"name": "kafka-ready"}

    def test_replica_counters(self, any_client):
        client, _ = any_client

        assert (
            client.get_deployment_entity_ready_replicas(V1Deployment(status=V1DeploymentStatus(ready_replicas=2))) == 2
        )
        assert client.get_deployment_entity_unavailable_replicas(DEPLOYMENTS[1]) == 1

    def test_set_replicas(self, any_client):
        client, apps = any_client
        apps.read_namespaced_deployment_scale.return_value = V1Scale(
            spec=V1ScaleSpec(replicas=1), status=V1ScaleStatus(replicas=1)
        )

        client.set_replicas_for_deployment_entity("kafka-ready", NAMESPACE, replicas=3)

        name, namespace, scale = apps.patch_namespaced_deployment_scale.call_args.args
        assert (name, namespace, scale.spec.replicas, scale.status.replicas) == ("kafka-ready", NAMESPACE, 3, 3)

    @pytest.mark.parametrize("current, expected", [(2, 3), (None, 1)])
    def test_scale_up(self, any_client, current, expected):
        client, apps = any_client
        apps.read_namespaced_deployment_scale.return_value = V1Scale(
            spec=V1ScaleSpec(replicas=current), status=V1ScaleStatus(replicas=current or 0)
        )

        client.scale_up_deployment_entity("kafka-ready", NAMESPACE)

        assert apps.patch_namespaced_deployment_scale.call_args.args[2].spec.replicas == expected

    @pytest.mark.parametrize("current, expected", [(2, 1), (0, 0), (None, 0)])
    def test_scale_down(self, any_client, current, expected):
        client, apps = any_client
        apps.read_namespaced_deployment_scale.return_value = V1Scale(
            spec=V1ScaleSpec(replicas=current), status=V1ScaleStatus(replicas=current or 0)
        )

        client.scale_down_deployment_entity("kafka-ready", NAMESPACE)

        assert apps.patch_namespaced_deployment_scale.call_args.args[2].spec.replicas == expected

    def test_create_patch_and_delete_delegate_to_apps_api(self, any_client):
        client, apps = any_client
        body = DEPLOYMENTS[0]

        client.create_deployment_entity(body, NAMESPACE)
        client.patch_namespaced_deployment_entity("kafka-ready", NAMESPACE, {"spec": {}})
        client.delete_deployment_entity("kafka-ready", NAMESPACE)

        apps.create_namespaced_deployment.assert_called_once_with(namespace=NAMESPACE, body=body)
        apps.patch_namespaced_deployment.assert_called_once_with("kafka-ready", NAMESPACE, {"spec": {}})
        apps.delete_namespaced_deployment.assert_called_once_with(name="kafka-ready", namespace=NAMESPACE)


class TestKubernetesClientClassification:
    def test_active_deployments_have_available_and_no_unavailable_replicas(self, kubernetes_client):
        assert kubernetes_client.get_active_deployment_entities_names_for_service(NAMESPACE, "kafka") == ["kafka-ready"]
        assert kubernetes_client.get_active_deployment_entities_count_for_service(NAMESPACE, "kafka") == 1

    def test_inactive_deployments_are_scaled_down_or_have_unavailable_replicas(self, kubernetes_client):
        assert kubernetes_client.get_inactive_deployment_entities_names_for_service(NAMESPACE, "kafka") == [
            "kafka-degraded",
            "kafka-scaled-down",
        ]
        assert kubernetes_client.get_inactive_deployment_entities_count_for_service(NAMESPACE, "kafka") == 2


class TestOpenShiftClientClassification:
    def test_active_deployments_have_no_unavailable_replicas(self, openshift_client):
        assert openshift_client.get_active_deployment_entities_names_for_service(NAMESPACE, "kafka") == [
            "kafka-ready",
            "kafka-scaled-down",
        ]
        assert openshift_client.get_active_deployment_entities_count_for_service(NAMESPACE, "kafka") == 2

    def test_inactive_deployments_have_no_replicas(self, openshift_client):
        assert openshift_client.get_inactive_deployment_entities_names_for_service(NAMESPACE, "kafka") == [
            "kafka-scaled-down"
        ]
        assert openshift_client.get_inactive_deployment_entities_count_for_service(NAMESPACE, "kafka") == 1

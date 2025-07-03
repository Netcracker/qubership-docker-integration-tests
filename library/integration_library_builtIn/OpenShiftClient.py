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

from kubernetes import client


class OpenShiftClient(object):
    def __init__(self, api_client):
        self.api_client = api_client
        self.k8s_apps_v1_client = client.AppsV1Api(api_client)
        self._patch_scale_dict = {'spec': {'replicas': 1}}

    def get_deployment_entity(self, name: str, namespace: str):
        return self.k8s_apps_v1_client.read_namespaced_deployment(name, namespace)

    def get_deployment_entities(self, namespace: str):
        return [deployment for deployment in self.k8s_apps_v1_client.list_namespaced_deployment(namespace).items]

    def get_deployment_entity_names_for_service(self, namespace: str, service: str, label: str = 'clusterName') -> list:
        deployments = self.get_deployment_entities(namespace)
        deployment_names = []
        for deployment in deployments:
            if deployment.spec.template.metadata.labels.get(label, '') == service:
                deployment_names.append(deployment.metadata.name)
        return deployment_names

    def get_inactive_deployment_entities_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> list:
        deployments = self.get_deployment_entities(namespace)
        inactive_deployments = []

        for deployment in deployments:
            if deployment.spec.template.metadata.labels.get(label, '') == service:
                if deployment.status.available_replicas == 0 or not deployment.status.replicas:
                    inactive_deployments.append(deployment)
        return inactive_deployments

    def get_inactive_deployment_entities_names_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> list:
        inactive_deployments = self.get_inactive_deployment_entities_for_service(
            namespace, service, label)
        inactive_deployment_names = []
        for deployment in inactive_deployments:
            inactive_deployment_names.append(deployment.metadata.name)
        return inactive_deployment_names

    def get_inactive_deployment_entities_count_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> int:
        deployments = self.get_deployment_entities(namespace)
        if not deployments:
            return 0
        return len(self.get_inactive_deployment_entities_for_service(namespace, service, label))

    def get_first_deployment_entity_name_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> str:
        deployments = self.get_deployment_entities(namespace)
        for deployment in deployments:
            if deployment.spec.template.metadata.labels.get(label, '') == service:
                return deployment.metadata.name
        return None

    def get_active_deployment_entities_for_service(self,
                                                   namespace: str,
                                                   service: str,
                                                   label: str = 'clusterName') -> list:
        deployments = self.get_deployment_entities(namespace)
        active_deployments = []

        for deployment in deployments:
            if deployment.spec.template.metadata.labels.get(label, '') == service \
                    and not deployment.status.unavailable_replicas \
                    and deployment.status.available_replicas != 0:
                active_deployments.append(deployment)
        return active_deployments

    def get_active_deployment_entities_names_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str = 'clusterName') -> list:
        active_deployments = self.get_active_deployment_entities_for_service(
            namespace, service, label)
        active_deployment_names = []
        for deployment in active_deployments:
            active_deployment_names.append(deployment.metadata.name)
        return active_deployment_names

    def get_active_deployment_entities_count_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str = 'clusterName') -> int:
        deployments = self.get_deployment_entities(namespace)
        if not deployments:
            return 0
        return len(self.get_active_deployment_entities_for_service(namespace, service, label))

    def get_deployment_entities_count_for_service(self, namespace: str, service: str, label: str = 'clusterName'):
        return len(self.get_deployment_entity_names_for_service(namespace, service, label))

    def get_deployment_scale(self, name: str, namespace: str):
        return self.k8s_apps_v1_client.read_namespaced_deployment_scale(name, namespace)

    def set_deployment_scale(self, name: str, namespace: str, scale):
        self.k8s_apps_v1_client.patch_namespaced_deployment_scale(
            name, namespace, scale)

    def set_replicas_for_deployment_entity(self, name: str, namespace: str, replicas: int = 1):
        scale = self.get_deployment_scale(name, namespace)
        scale.spec.replicas = replicas
        scale.status.replicas = replicas
        self.set_deployment_scale(name, namespace, scale)

    def scale_up_deployment_entity(self, name: str, namespace: str):
        scale = self.get_deployment_scale(name, namespace)
        if scale.spec.replicas is None:
            scale.spec.replicas = 1
        else:
            scale.spec.replicas += 1
        scale.status.replicas += 1
        self.set_deployment_scale(name, namespace, scale)

    def scale_down_deployment_entity(self, name: str, namespace: str):
        scale = self.get_deployment_scale(name, namespace)
        if scale.spec.replicas is None or not scale.spec.replicas:
            scale.spec.replicas = 0
        else:
            scale.spec.replicas -= 1
        if scale.status.replicas:
            scale.status.replicas -= 1
        self.set_deployment_scale(name, namespace, scale)

    def get_deployment_entity_pod_selector_labels(self, name: str, namespace: str) -> dict:
        deployment = self.get_deployment_entity(name, namespace)
        return deployment.spec.selector.match_labels if deployment else None

    def patch_namespaced_deployment_entity(self, name: str, namespace: str, body):
        self.k8s_apps_v1_client.patch_namespaced_deployment(
            name, namespace, body)

    def get_deployment_entity_ready_replicas(self, deployment):
        return deployment.status.ready_replicas

    def get_deployment_entity_unavailable_replicas(self, deployment):
        return deployment.status.unavailable_replicas

    def create_deployment_entity(self, body, namespace: str):
        return self.k8s_apps_v1_client.create_namespaced_deployment(namespace=namespace, body=body)

    def delete_deployment_entity(self, name: str, namespace: str):
        return self.k8s_apps_v1_client.delete_namespaced_deployment(name=name, namespace=namespace)

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

import ssl
import time
from typing import List

import kubernetes
import urllib3
import yaml
from deprecated import deprecated
from kubernetes import client, config
from kubernetes.stream import stream
from KubernetesClient import KubernetesClient
from OpenShiftClient import OpenShiftClient  # noqa: F401

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_kubernetes_api_client(config_file=None, context=None, persist_config=True):
    try:
        config.load_incluster_config()
        return patchK8sClient(kubernetes.client.ApiClient())
    except config.ConfigException:
        return patchK8sClient(kubernetes.config.new_client_from_config(
            config_file=config_file,
            context=context,
            persist_config=persist_config))


def patchK8sClient(api_client):
    ctx = ssl.create_default_context()
    ctx.verify_flags = ctx.verify_flags & ~ssl.VERIFY_X509_STRICT

    api_client.rest_client.pool_manager = urllib3.PoolManager(
        num_pools=4,
        ssl_context=ctx,
        **api_client.rest_client.pool_manager.connection_pool_kw,
    )
    return api_client


class PlatformLibrary(object):
    """This is a Robot Framework library to communicate with Kubernetes platform.

    = Table of contents =

    - `Usage`
    - `Client Versions`
    - `Examples`
    - `Importing`
    - `Shortcuts`
    - `Keywords`

    = Usage =

    This library uses Kubernetes client to communicate with Kubernetes API servers.
    The library supports both standard Kubernetes resources and custom resources through the CustomObjectsApi.

    = Client Versions =

    *Note!* `PlatformLibrary` uses particular versions of `kubernetes` python library which do not
    guaranteed backward capabilities. This library is used with Kubernetes 1.16 and higher.

    = Examples =

    These are examples of keywords usages.

    | `Get Deployment Entities`                          | elasticsearch-cluster   |
    | `Get Deployment Entity Names For Service`          | cassandra               | cassandra-backup-daemon | label=name |
    | `Get First Deployment Entity Name For Service`     | postgres-service        | monitoring-collector    | label=app  |
    | `Get Active Deployment Entities Count For Service` | cassandra               | cassandra-backup-daemon | label=name |
    | `Get Deployment Entities Count For Service`        | postgres-service        | monitoring-collector    | label=app  |
    | `Set Replicas For Deployment Entity`               | monitoring-collector    | postgres-service        |
    | `Scale Up Deployment Entity`                       | cassandra-backup-daemon | cassandra               |
    | `Scale Down Deployment Entity`                     | monitoring-collector    | postgres-service        |


    """  # noqa: E501
    ROBOT_LIBRARY_VERSION = '0.0.1'

    def __init__(self,
                 managed_by_operator="false",
                 config_file=None,
                 context=None,
                 persist_config=True):
        """A platform can be chosen between Kubernetes and OpenShift at library import time.

        Examples of `managed_by_operator` variable usage:

        | =Setting= | =Value=         | =Value=                     | =Comment=                      |
        | Library   | PlatformLibrary | managed_by_operator="true"  | Kubernetes client will be used |
        | Library   | PlatformLibrary | managed_by_operator="false" | OpenShift client will be used  |
        | Library   | PlatformLibrary |                             | OpenShift client will be used  |

        To login to Kubernetes API server the `PlatformLibrary` tries to use `in-cluster` config by default.
        It means that the library tries to read Kubernetes service account token in the current Kubernetes pod with
        trusted certs. If files do not exist default `kubeconfig` (`~/.kube/config`) setting is used. There is an
        ability to use custom `kubeconfig` file to get Kubernetes token.

        Examples of custom Kubernetes config file usage:
        | =Setting= | =Value=         | =Value=                            | =Value=               | =Value=              | =Comment=                                                                                                  |
        | Library   | PlatformLibrary | config_file=/mnt/kubeconfig/config | context=cluster/admin | persist_config=False | Custom config file will be used with predefined context - `cluster/admin`, GCP token will not be refreshed  |
        | Library   | PlatformLibrary | config_file=/mnt/kubeconfig/config | context=cluster/admin |                      | Custom config file will be used with predefined context - `cluster/admin`, GCP token will be refreshed      |
        | Library   | PlatformLibrary | config_file=/mnt/kubeconfig/config |                       |                      | Custom config file will be used with current context for provided file, GCP token will be refreshed        |
        | Library   | PlatformLibrary |                                    |                       |                      | Default config file will be used with current context for provided file, GCP token will be refreshed       |
        """  # noqa: E501

        self.k8s_api_client = get_kubernetes_api_client(config_file=config_file,
                                                        context=context,
                                                        persist_config=persist_config)

        self.platform_client = KubernetesClient(self.k8s_api_client)
        self.k8s_apps_v1_client = self.platform_client.k8s_apps_v1_client

        self.k8s_core_v1_client = client.CoreV1Api(self.k8s_api_client)
        self.custom_objects_api = client.CustomObjectsApi(self.k8s_api_client)
        self.networking_api = client.NetworkingV1Api(self.k8s_api_client)

    def get_custom_resources(self, api_version: str, kind: str, namespace: str) -> List[dict]:
        """
        Returns custom resources by project/namespace.
        :param api_version: ApiVersion to find resource
        :param kind: Kind to find resource
        :param namespace: namespace to find resource

        Example:
        | Get Custom Resources | v1alpha1 | integreatly.org | prometheus-operator |
        """
        group, version = api_version.split('/')
        return self.custom_objects_api.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=kind.lower() + 's'
        )['items']

    def get_custom_resource(self, api_version: str, kind: str, namespace: str, name: str) -> dict:
        """
        Returns custom resource by name and project/namespace.
        :param api_version: ApiVersion to find resource
        :param kind: Kind to find resource
        :param namespace: namespace to find resource
        :param name: name to find resource

        Example:
        | Get Custom Resource | v1alpha1 | integreatly.org | prometheus-operator | test_dashboard |
        """
        group, version = api_version.split('/')
        return self.custom_objects_api.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=kind.lower() + 's',
            name=name
        )

    def get_ingress_api_version(self):
        """
        Returns current api version of Ingress objects.

        Example:
        | Get Ingress Api Version |
        """
        return self.networking_api.get_api_resources().group_version

    def get_ingresses(self, namespace: str) -> List[dict]:
        """
        Returns list of Ingress objects in specified project/namespace.

        :param namespace: namespace to find ingresses

        Example:
        | Get Ingresses | cassandra |
        """
        return self.networking_api.list_namespaced_ingress(namespace).items

    def get_ingress(self, name: str, namespace: str) -> dict:
        """
        Returns ingress by name in specified project/namespace.

        :param namespace: namespace to find ingress
        :param name: name to find ingress

        Example:
        | Get Ingress | cassandra-ingress | cassandra |
        """
        return self.networking_api.read_namespaced_ingress(name, namespace)

    def get_ingress_url(self, name, namespace):
        """Returns url of given Ingress in project/namespace.

        :param namespace: namespace to find ingress
        :param name: name to find ingress

        Example:
        | Get Ingress Url | cassandra-ingress | cassandra |
        """
        ret = self.get_ingress(name, namespace)
        return "http://" + ret.spec.rules[0].host

    def get_routes(self, namespace: str) -> List[dict]:
        """
        Returns list of routes in specified project/namespace.

        :param namespace: namespace to find routes
        :return: a list of found routes in the namespace

        Example:
        | Get Routes | cassandra |
        """
        return self.custom_objects_api.list_namespaced_custom_object(
            group='route.openshift.io',
            version='v1',
            namespace=namespace,
            plural='routes'
        )['items']

    def get_route(self, name: str, namespace: str) -> dict:
        """
        Returns route by name in specified project/namespace.

        :param namespace: namespace to find route
        :param name: name to find route
        :return: a found route in the namespace

        Example:
        | Get Route | cassandra-route | cassandra |
        """
        return self.custom_objects_api.get_namespaced_custom_object(
            group='route.openshift.io',
            version='v1',
            namespace=namespace,
            plural='routes',
            name=name
        )

    def get_route_url(self, name, namespace):
        """Gets url of given Route in project/namespace.

        :param namespace: namespace to find route
        :param name: name to find route

        Example:
        | Get Route Url | cassandra-route | cassandra |
        """
        ret = self.get_route(name, namespace)
        return "http://" + ret.spec.host

    def create_namespaced_custom_object(self, group, version, namespace, plural, body):
        """Create Kubernetes custom object with body configuration as JSON object in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param body: the JSON schema of the Resource to create.

        Example:
        | Create Namespaced Custom Object | integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | dashboard_body |
        """  # noqa: E501
        return self.custom_objects_api.create_namespaced_custom_object(group, version, namespace, plural, body,
                                                                       pretty='true')

    def get_namespaced_custom_object(self, group, version, namespace, plural, name):
        """Returns existing Kubernetes custom object by provided group, version, plural, name in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param name: the name of custom object to return.

        Example:
        | Get Namespaced Custom Object | integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | dashboard_vault |
        """  # noqa: E501
        return self.custom_objects_api.get_namespaced_custom_object(group, version, namespace, plural, name)

    def get_namespaced_custom_object_status(self, group, version, namespace, plural, name):
        """Returns status of existing Kubernetes custom object by provided group, version, plural, name in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param name: the name of custom object to return.

        Example:
        | Get Namespaced Custom Object Status| integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | dashboard_vault |
        """  # noqa: E501
        return self.custom_objects_api.get_namespaced_custom_object_status(group, version, namespace, plural, name)

    def replace_namespaced_custom_object(self, group, version, namespace, plural, name, body):
        """Replaces Kubernetes custom object with body configuration as JSON object in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param name: the name of custom object to return.
        :param body: the JSON schema of the Resource to create.

        Example:
        | Replace Namespaced Custom Object | integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | test_dashboard | dashboard_body |
        """  # noqa: E501 # noqa: E501
        return self.custom_objects_api.replace_namespaced_custom_object(group, version, namespace, plural, name, body)

    def patch_namespaced_custom_object(self, group, version, namespace, plural, name, body):
        """Patches existing Kubernetes custom object by provided body in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param name: the name of custom object to update
        :param body: the JSON schema of the Resource to update.

        Example:
        | Patch Namespaced Custom Object | integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | dashboard_vault | body
        """  # noqa: E501
        return self.custom_objects_api.patch_namespaced_custom_object(group, version, namespace, plural, name, body)

    def delete_namespaced_custom_object(self, group, version, namespace, plural, name):
        """Delete existing custom object by provided group, api version, plural, name in project/namespace.

        :param group: the custom resource's group name
        :param version: the custom resource's version
        :param namespace: the custom resource's namespace
        :param plural: the custom resource's plural name. For TPRs this would be lowercase plural kind.
        :param name: the name of custom object to delete.

        Example:
        | Delete Namespaced Custom Object | integreatly.org | v1alpha1 | prometheus-operator | grafanadashboards | dashboard_vault |
        """  # noqa: E501
        return self.custom_objects_api.delete_namespaced_custom_object(group, version, namespace, plural, name)

    def get_daemon_sets(self, namespace: str) -> List[dict]:
        """
        Returns list of daemon sets in specified project/namespace.

        :param namespace: namespace to find daemon sets
        :return: a list of found daemon sets in the namespace

        Example:
        | Get Daemon Sets | prometheus-operator |
        """
        return self.k8s_apps_v1_client.list_namespaced_daemon_set(namespace).items

    def get_daemon_set(self, name: str, namespace: str) -> dict:
        """
        Returns daemon set by name in specified project/namespace.

        :param namespace: namespace to find daemon set
        :param name: name to find daemon set
        :return: a found daemon set in the namespace

        Example:
        | Get Daemon Set | node-exporter | prometheus-operator |
        """
        return self.k8s_apps_v1_client.read_namespaced_daemon_set(name, namespace)

    def get_service(self, name: str, namespace: str):
        """Returns Kubernetes `Service` configuration as JSON object.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Service | cassandra-dc-dc1 | cassandra |
        """
        return self.k8s_core_v1_client.read_namespaced_service(name, namespace)

    def create_service(self, body, namespace: str):
        """Creates Kubernetes `Service` with body configuration as JSON object in specified project/namespace.

        Example:
        | Create Service | <service_body> | cassandra |
        """
        return self.k8s_core_v1_client.create_namespaced_service(namespace=namespace, body=body)

    def create_service_from_file(self, file_path, namespace: str):
        """Creates Kubernetes `Service` by specified file path in project/namespace.
        The file must be in the yaml format.

        Example:
        | Create Service From File | <path>/service.yaml | cassandra |
        """

        body = self._parse_yaml_from_file(file_path)
        return self.create_service(body=body, namespace=namespace)

    def delete_service(self, name: str, namespace: str):
        """Deletes Kubernetes `Service` by specified name in project/namespace.

        Example:
        | Delete Service | test-application | cassandra |
        """

        return self.k8s_core_v1_client.delete_namespaced_service(name=name, namespace=namespace)

    def get_service_selector(self, name: str, namespace: str) -> dict:
        """Returns Kubernetes `Service` labels selector as dictionary.
        This selector is used by service to look up relative Kubernetes `pods`.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Service Selector | cassandra-dc-dc1 | cassandra |
        """
        service = self.k8s_core_v1_client.read_namespaced_service(
            name, namespace)
        return service.spec.selector

    def get_deployment_entity(self, name: str, namespace: str):
        """Returns `deployment/deployment config` configuration.
         Example:
         | Get Deployment Entity | elasticsearch-1 | elasticsearch-service |
        """
        return self.platform_client.get_deployment_entity(name, namespace)

    def get_deployment_entities(self, namespace: str) -> list:
        """Returns list of `deployments` which belong to taken `namespace`.
        Each element of the list is `object` which describes current `deployment` configuration.

        Example:

        | Get Deployment Entities | kafka-cluster |
        """
        return self.platform_client.get_deployment_entities(namespace)

    def get_deployment_entity_names_for_service(self, namespace: str, service: str, label: str = 'clusterName') -> list:
        """Returns list of `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all `deployment entity` names by
        namespace/project and label (`label` argument is name of label, `service` argument is value).

        Examples:
        | Get Deployment Entity Names For Service | kafka-cluster    | kafka                |
        | Get Deployment Entity Names For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_deployment_entity_names_for_service(namespace, service, label)

    def get_first_deployment_entity_name_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> str:
        """Returns first found `deployment`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds first `deployment entity` name by
        namespace/project and label (`label` argument is name of label, `service` argument is the value of this label).

        Examples:
        | Get First Deployment Entity Name For Service | kafka-cluster    | kafka                |
        | Get First Deployment Entity Name For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_first_deployment_entity_name_for_service(namespace, service, label)

    def get_inactive_deployment_entities_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> list:
        """Returns list of inactive `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all inactive (there are no available replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its.

        Examples:
        | Get Inactive Deployment Entities For Service | kafka-cluster    | kafka                |
        | Get Inactive Deployment Entities For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_inactive_deployment_entities_for_service(namespace, service, label)

    def get_inactive_deployment_entities_names_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> list:
        """Returns list with names of inactive `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all inactive (there are no available replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its names.

        Examples:
        | Get Inactive Deployment Entities Names For Service | kafka-cluster    | kafka                |
        | Get Inactive Deployment Entities Names For Service | postgres-service | monitoring-collector | label=app |
        """  # noqa: E501
        return self.platform_client.get_inactive_deployment_entities_names_for_service(namespace, service, label)

    def get_inactive_deployment_entities_count_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> int:
        """Returns number of inactive `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all inactive (there are no unavailable replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its count.

        Examples:
        | Get Inactive Deployment Entities Count For Service | kafka-cluster    | kafka                |
        | Get Inactive Deployment Entities Count For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_inactive_deployment_entities_count_for_service(namespace, service, label)

    def get_inactive_deployment_entities_count(self, deployment_entity_names: list, namespace: str) -> int:
        """Returns number of inactive `deployments/deployment configs`. `Deployment entity` is inactive if it has no
        replicas. Deployment entities are found by name and project/namespace.

        Example:
        | Get Inactive Deployment Entities Count | <list_of_deployment_entity_names> | cassandra |
        """
        counter = 0
        for deployment_entity_name in deployment_entity_names:
            deployment_entity = self.get_deployment_entity(
                deployment_entity_name, namespace)
            if not deployment_entity.status.replicas:
                counter += 1
        return counter

    def get_active_deployment_entities_for_service(self,
                                                   namespace: str,
                                                   service: str,
                                                   label: str = 'clusterName') -> list:
        """Returns list of active `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all active (there are no unavailable replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its.

        Examples:
        | Get Active Deployment Entities For Service | kafka-cluster    | kafka                |
        | Get Active Deployment Entities For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_active_deployment_entities_for_service(namespace, service, label)

    def get_active_deployment_entities_names_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str = 'clusterName') -> list:
        """Returns list with names of active `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all active (there are no unavailable replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its names.

        Examples:
        | Get Active Deployment Entities Names For Service | kafka-cluster    | kafka                |
        | Get Active Deployment Entities Names For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_active_deployment_entities_names_for_service(namespace, service, label)

    def get_active_deployment_entities_count_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str = 'clusterName') -> int:
        """Returns number of active `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all active (there are no unavailable replicas)
        `deployment entities` by namespace/project, label (`label` argument is name of label, `service` argument is the
        value of this label) and returns its count.

        Examples:
        | Get Active Deployment Entities Count For Service | kafka-cluster    | kafka                |
        | Get Active Deployment Entities Count For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_active_deployment_entities_count_for_service(namespace, service, label)

    def get_active_deployment_entities_count(self, deployment_entity_names: list, namespace: str) -> int:
        """Returns number of active `deployments`. `Deployment entity` is active if it has no
        replicas in unavailable status. Deployment entities are found by name and project/namespace.

        Example:
        | Get Active Deployment Entities Count | <list_of_deployment_entity_names> | cassandra |
        """
        counter = 0
        for deployment_entity_name in deployment_entity_names:
            deployment_entity = self.get_deployment_entity(
                deployment_entity_name, namespace)
            if not self.platform_client.get_deployment_entity_unavailable_replicas(deployment_entity) \
                    and deployment_entity.status.replicas:
                counter += 1
        return counter

    def create_deployment_entity(self, body, namespace: str):
        """Creates `deployment` with body configuration as JSON object in specified project/namespace.

        Examples:
        | Create Deployment Entity | <body_of_deployment_entity> | elasticsearch-service |
        """
        return self.platform_client.create_deployment_entity(body=body, namespace=namespace)

    def create_deployment_entity_from_file(self, file_path, namespace: str):
        """Creates `deployment` by specified file path in project/namespace. The file must be in the yaml format.

        Examples:
        | Create Deployment Entity From File | <path>/deployment.yaml | elasticsearch-service |
        """
        body = self._parse_yaml_from_file(file_path)

        return self.create_deployment_entity(body=body, namespace=namespace)

    def delete_deployment_entity(self, name: str, namespace: str):
        """Deletes `deployment` by specified name in project/namespace.

        Examples:
        | Delete Deployment Entity | test-application | prometheus-operator |
        """
        return self.platform_client.delete_deployment_entity(name=name, namespace=namespace)

    def check_service_is_scaled(self, deployment_entity_names, namespace: str, direction="up",
                                timeout=300) -> bool:
        """Returns `True` if all given `deployments` are scaled. They can be scaled "up" or "down".
        `direction` variable defines direction of scale and should be set without quote symbols.
        "down" direction means  that all given deployment entities have no replicas.
        "up" direction means that all given deployment entities have only "ready" replicas.
        Deployment entities are found by name and project/namespace.
        Deployment entities names can be passed as a list or string value.
        In case of string value type use a space separator.
        `timeout` variable (in seconds) is used to cancel waiting circle.
        Method raises an Exception if `direction` variable is not "up" or "down" or it passed with quote symbols.

        Examples:
        | Check Service Is Scaled | <list_of_deployment_entity_names> | elasticsearch-service | direction=down | timeout=450 |
        | Check Service Is Scaled | <list_of_deployment_entity_names> | elasticsearch-service | direction=down |
        | Check Service Is Scaled | deployment_entity_name | elasticsearch-service |
        """  # noqa: E501
        direction = direction.lower()

        if direction in ('"up"', '"down"', "'up'", "'down'"):
            raise Exception('set direction parameter (up or down) without quote symbols ""')
        elif direction not in ("up", "down"):
            raise Exception(f'direction argument should be "up" or "down" but {direction} is given')

        if isinstance(deployment_entity_names, str):
            deployment_entity_names = list(deployment_entity_names.split(' '))

        timeout_start = time.time()
        check_func = self.get_active_deployment_entities_count \
            if direction == "up" else self.get_inactive_deployment_entities_count

        while time.time() <= timeout_start + timeout:
            if len(deployment_entity_names) == check_func(deployment_entity_names, namespace):
                return True
            time.sleep(5)

        return False

    def scale_down_deployment_entities_by_service_name(self,
                                                       service_name: str,
                                                       namespace: str,
                                                       with_check: bool = False,
                                                       timeout: int = 300):
        """Scales down (set 0 replicas) all `deployments` which manage the same `Pods` as given `Service`.
        Deployment entities are found by Service name and namespace.
        `with_check` is used to wait till all Deployment entities will have no replicas.
        if `with_check=True` `timeout` variable (in seconds) is used and specifies timeout for checker.

        Examples:
        | Scale Down Deployment Entities By Service Name | elasticsearch | elasticsearch-service | with_check=True | timeout=450 |
        | Scale Down Deployment Entities By Service Name | elasticsearch | elasticsearch-service | with_check=True |
        | Scale Down Deployment Entities By Service Name | elasticsearch | elasticsearch-service |
        """  # noqa: E501
        deployment_entity_names = self.get_deployment_entity_names_by_service_name(
            service_name, namespace)
        for deployment_entity_name in deployment_entity_names:
            self.set_replicas_for_deployment_entity(
                deployment_entity_name, namespace, replicas=0)
        if with_check:
            self.check_service_is_scaled(
                deployment_entity_names, namespace, direction="down", timeout=timeout)

    def scale_up_deployment_entities_by_service_name(self,
                                                     service_name: str,
                                                     namespace: str,
                                                     with_check: bool = False,
                                                     timeout: int = 300,
                                                     **kwargs):
        """Scales up `deployments` which manage the same `Pods` as given `Service`.
        If `replicas` parameter is presented method set it value to all found Deployment Entities as replicas value.
        If this parameter is not presented for all found Deployment Entities number of replicas will be increase on one.
        Actually, `replicas=0` can be used to scale down found `Deployment Entities` but for this purpose it is
        recommended to use the `Scale Down Deployment Entities By Service Name` method.
        Deployment Entities are found by Service name and namespace.
        `with_check` is used to wait till all Deployment Entities will have no replicas in not "ready" status.
        if `with_check=True` `timeout` variable (in seconds) is used and specifies timeout for checker.

        Examples:
        | Scale Up Deployment Entities By Service Name | elasticsearch | elasticsearch-service | replicas=2      | with_check=True | timeout=450 |
        | Scale Up Deployment Entities By Service Name | elasticsearch | elasticsearch-service | with_check=True | timeout=450 |
        | Scale Up Deployment Entities By Service Name | elasticsearch | elasticsearch-service | with_check=True |
        | Scale Up Deployment Entities By Service Name | elasticsearch | elasticsearch-service |
        """  # noqa: E501
        replicas = kwargs.get('replicas', None)
        if replicas is not None:
            replicas = int(replicas)
        deployment_entity_names = self.get_deployment_entity_names_by_service_name(
            service_name, namespace)
        for deployment_entity_name in deployment_entity_names:
            if replicas is not None:
                self.set_replicas_for_deployment_entity(
                    deployment_entity_name, namespace, replicas=replicas)
            else:
                self.scale_up_deployment_entity(
                    deployment_entity_name, namespace)
        if with_check:
            direction = "down" if replicas == 0 else "up"
            self.check_service_is_scaled(
                deployment_entity_names, namespace, direction=direction, timeout=timeout)

    def get_deployment_entities_count_for_service(self, namespace: str, service: str, label: str = 'clusterName'):
        """Returns number of `deployments`.
        Supposed that all deployment entities are matched on the particular Kubernetes service. This matching is
        implemented by special `label` for deployment entity. The name of this `label` is specified by developer,
        value is Kubernetes `service` name. The keyword finds all `deployment entities` by namespace/project,
        label (`label` argument is name of label, `service` argument is value) and returns its count.

        Examples:
        | Get Deployment Entities Count For Service | kafka-cluster    | kafka                |
        | Get Deployment Entities Count For Service | postgres-service | monitoring-collector | label=app |
        """
        return self.platform_client.get_deployment_entities_count_for_service(namespace, service, label)

    def set_replicas_for_deployment_entity(self, name: str, namespace: str, replicas: int = 1):
        """Sets number of replicas for found `deployment`.
        Pair of `name` and `namespace` specifies unique deployment entity. Method finds deployment entity by
        name, namespace and vertical scales it (patches deployment entity and set given number of replicas).
        For each additional replica new Kubernetes pod will be created.

        Example:
        | Set Replicas For Deployment Entity | cassandra-backup-daemon | cassandra        | replicas=3 |
        | Set Replicas For Deployment Entity | monitoring-collector    | postgres-service |
        """
        self.platform_client.set_replicas_for_deployment_entity(
            name, namespace, replicas)

    def scale_up_deployment_entity(self, name: str, namespace: str):
        """Increases by one number of replicas for found `deployment`.
        Pair of `name` and `namespace` specifies unique deployment entity. Method finds
        deployment entity by name, namespace, recognizes current number of replicas and vertical scales it
        (patches deployment entity and increases number of replicas by one - new Kubernetes pod will be created).

        Example:
        | Scale Up Deployment Entity | elasticsearch-1 | elasticsearch-cluster |
        """
        self.platform_client.scale_up_deployment_entity(name, namespace)

    def scale_down_deployment_entity(self, name: str, namespace: str):
        """Decreases by one number of replicas for found `deployment`.
        Pair of `name` and `namespace` specifies unique deployment entity. Method finds
        deployment entity by name, namespace, recognizes current number of replicas and vertical scales it
        (patches deployment entity and decreases number of replicas by one - some Kubernetes pod will be removed).

        Example:
        | Scale Down Deployment Entity | elasticsearch-1 | elasticsearch-cluster |
        """
        self.platform_client.scale_down_deployment_entity(name, namespace)

    def get_deployment_entity_pod_selector_labels(self, name: str, namespace: str) -> dict:
        """Returns a dictionary of matched labels for `deployment`.
        This matched labels are used by `deployment` to watch for it pods.
        Deployment entity name plus namespace defines unique deployment entity.
        Method finds deployment entity and returns selector labels for it.

        Example:
        | Get Deployment Entity Pod Selector Labels | elasticsearch-1 | elasticsearch-cluster |
        """
        return self.platform_client.get_deployment_entity_pod_selector_labels(name, namespace)

    def get_deployment_entity_names_by_selector(self, namespace: str, selector: dict) -> list:
        """Returns list of `deployment` names by given selector.
        Method finds deployment entity by it own `pod` selector. The deployment entity looks up
        relative pods by own label selector. If this label selector contains all labels from `selector` variable
        deployment entity is added to the result list.

        Example:
        | Get Deployment Entity Names By Selector | elasticsearch-service | <dictionary_with_labels> |
        """
        deployment_entities = self.get_deployment_entities(namespace)
        return [deployment_entity.metadata.name for deployment_entity in deployment_entities
                if self._do_labels_satisfy_selector(deployment_entity.spec.template.metadata.labels, selector)]

    def get_deployment_entity_names_by_service_name(self, service_name: str, namespace: str) -> list:
        """Returns list of `deployment` names by given Kubernetes service name and `namespace`.
        There is no direct mapping between `deployment entity` and `service`. Supposed that deployment
        entity watches the same kubernetes `pods` as Kubernetes service. So the `deployment entity`
        matches to the `service` by the transitivity property.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Deployment Entity Names By Service Name | monitoring-collector | postgres-service |
        """
        selector = self.get_service_selector(service_name, namespace)
        return self.get_deployment_entity_names_by_selector(namespace, selector)

    def get_pod_names_for_deployment_entity(self, deployment_entity_name: str, namespace: str) -> list:
        """Returns a list of Kubernetes pod names which will be found by `deployment entity` name and namespace.

        Example:
        | Get Pod Names For Deployment Entity | elasticsearch-1 | elasticsearch-cluster |
        """
        matched_labels = self.get_deployment_entity_pod_selector_labels(
            deployment_entity_name, namespace)
        pods = self.get_pods(namespace)
        if not pods or not matched_labels:
            return []
        return [pod.metadata.name for pod in pods
                if self._do_labels_satisfy_selector(pod.metadata.labels, matched_labels)]

    @staticmethod
    def _do_labels_satisfy_selector(labels: dict, selector: dict):
        if selector is None or not isinstance(selector, dict):
            return False
        if labels is None or not isinstance(labels, dict):
            return False
        selector_pairs = list(selector.items())
        label_pairs = list(labels.items())
        if len(selector_pairs) > len(label_pairs):
            return False
        for pair in selector_pairs:
            if pair not in label_pairs:
                return False
        return True

    @staticmethod
    def _parse_yaml_from_file(file_path):
        return yaml.safe_load(open(file_path))

    def patch_namespaced_deployment_entity(self, name: str, namespace: str, body):
        """Patches `deployment` by new body.
        Deployment entity is found by name and namespace.
        `body` is a part of deployment entity spec which should be patched.

        Method raises an Exception if deployment entity is not found.

        Example:
        | Patch Namespaced Deployment Entity | elasticsearch-1 | elasticsearch-cluster | <part_of_deployment_entity_spec> |
        """  # noqa: E501
        self.platform_client.patch_namespaced_deployment_entity(
            name, namespace, body)

    def get_environment_variables_for_deployment_entity_container(self,
                                                                  name: str,
                                                                  namespace: str,
                                                                  container_name: str,
                                                                  variable_names: list) -> dict:
        """Returns a dictionary of `deployment` environment variables (key-values) for container.
        Deployment entity is found by name and namespace.
        `container_name` specifies name of docker container associated with environment variables (parameter is
        required).
        `variable_names` parameter specifies environment variable names for environment variables which should be
        returned as dictionary.

        Method raises an Exception if deployment entity is not found.

        Example:
        | Get Environment Variables For Deployment Entity Container | elasticsearch-0 | elasticsearch-service | elasticsearch | <list_of_variable_names> |
        """  # noqa: E501
        entity = self.get_deployment_entity(name, namespace)
        return self._get_environment_variables_for_container(entity, container_name, variable_names)

    def set_environment_variables_for_deployment_entity_container(self,
                                                                  name: str,
                                                                  namespace: str,
                                                                  container_name: str,
                                                                  variables_to_change: dict):
        """Changes values for given environment variables per `deployment` container.
        Deployment entity is found by name and namespace.
        `container_name` specifies name of docker container associated with environment variables (parameter is
        required).
        `variables_to_change` parameter specifies a dictionary of variables to update. If container environment variable
        names do not contain any `update_variables` dictionary key then this `update_variables` dictionary pair is
        redundant and will be ignored.

        Method raises an Exception if deployment entity is not found.

        Example:
        | Set Environment Variables For Deployment Entity Container | elasticsearch-1 | elasticsearch-cluster | elasticsearch | <dictionary_of_variables_to_change> |
        """  # noqa: E501
        entity = self.get_deployment_entity(name, namespace)
        self._prepare_entity_with_environment_variables_for_container(
            entity, container_name, variables_to_change)
        self.patch_namespaced_deployment_entity(name, namespace, entity)

    def _get_environment_variables_for_container(self,
                                                 entity,
                                                 container_name: str,
                                                 variable_names: list) -> dict:
        environments = self._get_environments_for_container(
            entity.spec.template.spec.containers, container_name)
        return self._get_env_variables(environments, variable_names)

    def _prepare_entity_with_environment_variables_for_container(self,
                                                                 entity,
                                                                 container_name: str,
                                                                 variables_to_update: dict):
        environments = self._get_environments_for_container(
            entity.spec.template.spec.containers, container_name)

        def set_new_variables(dicts: list, params: dict):
            for dictionary in dicts:
                if dictionary.name in params.keys():
                    dictionary.value = params[dictionary.name]

        set_new_variables(environments, variables_to_update)

    @staticmethod
    def _get_environments_for_container(containers, container_name):
        environments = None
        for container in containers:
            if container.name == container_name:
                environments = container.env
        return environments

    @staticmethod
    def _get_env_variables(dicts: list, params: list, ignore_reference=True):
        if not dicts:
            return None
        result = {}
        for dictionary in dicts:
            if dictionary.name in params:
                if not ignore_reference:
                    result[dictionary.name] = dictionary.value if dictionary.value is not None else ""
                elif dictionary.value is not None:
                    result[dictionary.name] = dictionary.value
        return result

    def get_stateful_set(self, name: str, namespace: str):
        """Returns `Stateful Set` configuration
        `Stateful Set` is found by name and namespace.

        Method raises an Exception if Stateful Set is not found.

        Example:
        | Get Stateful Set | cassandra0 | cassandra |
        """
        return self.k8s_apps_v1_client.read_namespaced_stateful_set(name, namespace)

    def get_stateful_sets(self, namespace: str) -> list:
        """Returns list of `Stateful Sets` by namespace.

        Example:
        | Get Stateful Sets | cassandra |
        """
        return self.k8s_apps_v1_client.list_namespaced_stateful_set(namespace).items

    def get_stateful_set_names_by_label(self, namespace: str, label_value: str, label_name: str = 'service') -> list:
        """Returns list of `Stateful Set` names by namespace and the particular label.
        `Label` is a "key-value" pair where key is `label_name` variable and value is `label_value`. If a Stateful Set
        contains this `label` its name is added to the result list.

        Example:
        | Get Stateful Set Names By Label | cassandra | cassandra-dc-dc2  | label_name=app |
        | Get Stateful Set Names By Label | cassandra | cassandra-cluster |
        """
        stateful_sets = self.get_stateful_sets(namespace)
        return [stateful_set.metadata.name for stateful_set in stateful_sets
                if stateful_set.metadata.labels.get(label_name, "") == label_value]

    @deprecated(reason="Use get_stateful_set_replicas_count")
    def get_stateful_set_replica_counts(self, name: str, namespace: str) -> int:
        """Returns replicas number for the particular `Stateful Set`.
        The `Stateful Set` is found by its `name` and namespace. Number of replicas is number of Kubernetes
        `pods` which current Stateful Set should create and manage. Actually some pods may be not in "running" status.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Get Stateful Set Replica Counts | cassandra1 | cassandra |
        """
        return self.get_stateful_set_replicas_count(name, namespace)

    def get_stateful_set_replicas_count(self, name: str, namespace: str) -> int:
        """Returns replicas number for the particular `Stateful Set`.
        The `Stateful Set` is found by its `name` and namespace. Number of replicas is number of Kubernetes
        `pods` which current Stateful Set should create and manage. Actually some pods may be not in "running" status.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Get Stateful Set Replicas Count | cassandra1 | cassandra |
        """
        stateful_set = self.k8s_apps_v1_client.read_namespaced_stateful_set(
            name, namespace)
        return stateful_set.spec.replicas

    def get_stateful_set_ready_replicas_count(self, name: str, namespace: str) -> int:
        """Returns ready replicas number for the particular `Stateful Set`.
        The `Stateful Set` is found by its `name` and namespace. Number of replicas is number of Kubernetes
        `pods` which current Stateful Set should create and manage. Actually some pods may be not in "running" status.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Get Stateful Set Ready Replicas Count | cassandra1 | cassandra |
        """
        stateful_set = self.k8s_apps_v1_client.read_namespaced_stateful_set(
            name, namespace)
        return stateful_set.status.ready_replicas

    @deprecated(reason="Use get_active_stateful_sets_count")
    def get_active_stateful_sets_counts(self, namespace: str, selector: dict) -> int:
        """Returns number of active `Stateful Sets`.
        `Stateful Sets` are found by namespace and given label selector. `selector` is a dictionary which should
        be contained by the particular Stateful Set labels. Method recognizes a Stateful Set as active if all its
        replicas are active. It means that all relative `pods` are in "running" status.

        Example:
        | Get Active Stateful Sets Counts | postgres-service | <selector dictionary> |
        """
        stateful_sets = self.get_stateful_sets(namespace)
        count = 0
        for stateful_set in stateful_sets:
            if self._do_labels_satisfy_selector(stateful_set.metadata.labels, selector):
                count += stateful_set.status.ready_replicas == stateful_set.status.replicas
        return count

    def get_active_stateful_sets_count(self, stateful_set_names: list, namespace: str) -> int:
        """Returns number of active Stateful Sets. `Stateful set` is active if all of it replicas
        are in "ready" status.
        Stateful Sets are found by name and namespace.

        Example:
        | Get Active Stateful Sets Count | <list_of_stateful_set_names> | cassandra |
        """
        counter = 0
        for stateful_set_name in stateful_set_names:
            stateful_set = self.get_stateful_set(stateful_set_name, namespace)
            if stateful_set.status.replicas == stateful_set.status.ready_replicas:
                counter += 1
        return counter

    @deprecated(reason="Use get_inactive_stateful_sets_count")
    def get_inactive_stateful_set_count(self, stateful_set_names: list, namespace: str) -> int:
        """Returns number of inactive Stateful Sets. `Stateful set` is inactive if it has no replicas
        or has replica in not "ready" status. Stateful Sets are found by name and namespace.

        Example:
        | Get Inactive Stateful Set Count | <list_of_stateful_set_names> | cassandra |
        """
        return self.get_inactive_stateful_sets_count(stateful_set_names, namespace)

    def get_inactive_stateful_sets_count(self, stateful_set_names: list, namespace: str) -> int:
        """Returns number of inactive Stateful Sets. `Stateful set` is inactive if it has no replicas
        or has replica in not "ready" status. Stateful Sets are found by name and namespace.

        Example:
        | Get Inactive Stateful Sets Count | <list_of_stateful_set_names> | cassandra |
        """
        counter = 0
        for stateful_set_name in stateful_set_names:
            stateful_set = self.get_stateful_set(stateful_set_name, namespace)
            if not stateful_set.status.replicas or stateful_set.status.replicas != stateful_set.status.ready_replicas:
                counter += 1
        return counter

    # TODO: refactor this method with the same one for deployment entities
    def check_service_of_stateful_sets_is_scaled(self, stateful_set_names, namespace: str, direction="up",
                                                 timeout=300) -> bool:
        """Returns `True` if all given Stateful Sets are scaled. They can be scaled "up" or "down".
        `direction` variable defines direction of scale and should be set without quote symbols. "down" direction means
        that all given Stateful Sets have no replicas. "up" direction means that all given Stateful Sets have only
        "ready" replicas. Stateful Sets are found by name and namespace. Stateful Sets names can be passed as a
        list or string value. In case of string value type use a space separator. `timeout` variable (in seconds) is used
        to cancel waiting circle.
        Method raises an Exception if `direction` variable is not "up" or "down" or it passed with quote symbols.

        Examples:
        | Check Service Of Stateful Sets Is Scaled | <list_of_stateful_set_names> | cassandra | direction=down | timeout=450 |
        | Check Service Of Stateful Sets Is Scaled | <list_of_stateful_set_names> | cassandra | direction=up   |
        | Check Service Of Stateful Sets Is Scaled | stateful_set_name | cassandra |
        """  # noqa: E501

        direction = direction.lower()
        if direction in ('"up"', '"down"', "'up'", "'down'"):
            raise Exception('set direction parameter (up or down) without quote symbols ""')
        elif direction not in ("up", "down"):
            raise Exception(f'direction argument should be "up" or "down" but {direction} is given')

        if isinstance(stateful_set_names, str):
            stateful_set_names = list(stateful_set_names.split(' '))

        timeout_start = time.time()
        check_func = self.get_active_stateful_sets_count \
            if direction == "up" else self.get_inactive_stateful_set_count
        while True:
            if len(stateful_set_names) == check_func(stateful_set_names, namespace):
                return True
            if time.time() > timeout_start + timeout:
                return False
            time.sleep(5)

    def scale_down_stateful_sets_by_service_name(self,
                                                 service_name: str,
                                                 namespace: str,
                                                 with_check: bool = False,
                                                 timeout: int = 300):
        """Scales down (set 0 replicas) all `Stateful Sets` which manage the same `Pods` as given `Service`.
        Stateful Sets are found by Service name and namespace.
        `with_check` is used to wait till all Stateful Sets will have no replicas.
        `timeout` variable (in seconds) is used only if `with_check=True` and specifies timeout for checker.

        Example:
        | Scale Down Stateful Sets By Service Name | cassandra | cassandra | with_check=True | timeout=450 |
        | Scale Down Stateful Sets By Service Name | cassandra | cassandra | with_check=True |
        | Scale Down Stateful Sets By Service Name | cassandra | cassandra |
        """
        stateful_set_names = self.get_stateful_set_names_by_service_name(
            service_name, namespace)
        for stateful_set_name in stateful_set_names:
            self.set_replicas_for_stateful_set(
                stateful_set_name, namespace, replicas=0)
        if with_check:
            self.check_service_of_stateful_sets_is_scaled(stateful_set_names, namespace, direction="down",
                                                          timeout=timeout)

    # TODO: Add an ability to do it with ordering
    def scale_up_stateful_sets_by_service_name(self,
                                               service_name: str,
                                               namespace: str,
                                               with_check: bool = False,
                                               timeout: int = 300,
                                               **kwargs):
        """Scales up `Stateful Sets` which manage the same `Pods` as given `Service`.
        If `replicas` parameter is presented method set it value to all found Stateful Sets as replicas value. If this
        parameter is not presented for all found Stateful Sets number of replicas will be increase on one. Actually,
        `replicas=0` can be used to scale down found `Stateful Sets` but `Scale Down Stateful Sets By Service Name`
        method recommended for this purpose.
        Stateful Sets are found by Service name and namespace.
        `with_check` is used to wait till all Stateful Sets will have no replicas in not "ready" status.
        `timeout` variable (in seconds) is used only if `with_check=True` and specifies timeout for checker.

        Examples:
        | Scale Up Stateful Sets By Service Name | cassandra | cassandra | replicas=2      | with_check=True | timeout=250 |
        | Scale Up Stateful Sets By Service Name | cassandra | cassandra | with_check=True | timeout=250     |
        | Scale Up Stateful Sets By Service Name | cassandra | cassandra | with_check=True |
        | Scale Up Stateful Sets By Service Name | cassandra | cassandra |
        """  # noqa: E501
        replicas = kwargs.get('replicas', None)
        if replicas is not None:
            replicas = int(replicas)
        stateful_set_names = self.get_stateful_set_names_by_service_name(
            service_name, namespace)
        for stateful_set_name in stateful_set_names:
            if replicas is not None:
                self.set_replicas_for_stateful_set(
                    stateful_set_name, namespace, replicas=replicas)
            else:
                self.scale_up_stateful_set(stateful_set_name, namespace)
        if with_check:
            direction = "down" if replicas is not None and replicas == 0 else "up"
            self.check_service_of_stateful_sets_is_scaled(stateful_set_names, namespace, direction=direction,
                                                          timeout=timeout)

    def get_stateful_set_pod_selector(self, name: str, namespace: str) -> dict:
        """Returns a Stateful Set labels selector as dictionary.
        Stateful Set labels selector is dictionary of labels which are used to look up relative Kubernetes `pods`
        for the Stateful Set. The Stateful Set is found by name and namespace.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Get Stateful Set Pod Selector | cassandra0 | cassandra |
        """
        stateful_set = self.k8s_apps_v1_client.read_namespaced_stateful_set(
            name, namespace)
        return stateful_set.spec.selector.match_labels

    def get_stateful_set_names_by_selector(self, namespace: str, selector: dict) -> list:
        """Returns list of Kubernetes Stateful Sets by given labels selector.
        Method finds `Stateful Sets` by it own `pod` selector. The stateful set looks up
        relative pods by own label selector. If this label selector contains all labels from `selector` variable
        Stateful Set is added to the result list.

        Example:
        | Get Stateful Set Names By Selector | cassandra | <selector_dictionary> |
        """
        stateful_sets = self.get_stateful_sets(namespace)
        return [stateful_set.metadata.name for stateful_set in stateful_sets
                if self._do_labels_satisfy_selector(stateful_set.spec.template.metadata.labels, selector)]

    def get_stateful_set_names_by_service_name(self, service_name: str, namespace: str) -> list:
        """Returns list of `Stateful Set` names by given Kubernetes service name and `namespace`.
        There is no direct mapping between `Stateful Set` and `service`. Supposed that Stateful Set watches the
        same Kubernetes `pods` as Kubernetes service. So the `Stateful Set` matches to the `service` by the
        transitivity property.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Stateful Set Names By Service Name | cassandra-dc-dc1 | cassandra |
        """
        selector = self.get_service_selector(service_name, namespace)
        return self.get_stateful_set_names_by_selector(namespace, selector)

    def set_replicas_for_stateful_set(self, name: str, namespace: str, replicas: int = 1):
        """Sets predefined number of replicas for found Stateful Set.
        Method looks up a Stateful Set by name and namespace and set number of replicas for it.
        It means that the Stateful Set should create and manage given number of Kubernetes `pods`.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Examples:
        | Set Replicas For Stateful Set | cassandra-dc-dc1 | cassandra | replicas=2 |
        | Set Replicas For Stateful Set | cassandra-dc-dc1 | cassandra |
        """
        scale = self.k8s_apps_v1_client.read_namespaced_stateful_set_scale(
            name, namespace)
        scale.spec.replicas = replicas
        self.k8s_apps_v1_client.patch_namespaced_stateful_set(
            name, namespace, scale)

    def scale_up_stateful_set(self, name: str, namespace: str):
        """Increases by one number of replicas for found `Stateful Set`.
        Pair of `name` and `namespace` specifies unique `Stateful Set`. Method finds
        `Stateful Set` by name, namespace, recognizes current number of replicas and scales it
        (patches `Stateful Set` and increases number of replicas by one - new Kubernetes `pod` will be created).

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Scale Up Stateful Set | cassandra0 | cassandra |
        """
        scale = self.k8s_apps_v1_client.read_namespaced_stateful_set_scale(
            name, namespace)
        if scale.spec.replicas is None:
            scale.spec.replicas = 1
        else:
            scale.spec.replicas += 1
        self.k8s_apps_v1_client.patch_namespaced_stateful_set(
            name, namespace, scale)

    def scale_down_stateful_set(self, name: str, namespace: str):
        """Decreases by one number of replicas for found `Stateful Set`.
        Pair of `name` and `namespace` specifies unique `Stateful Set`. Method finds
        `Stateful Set` by name, namespace, recognizes current number of replicas and scales it
        (patches `Stateful Set` and decreases number of replicas by one - some Kubernetes `pod` will be removed).

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Scale Down Stateful Set | cassandra0 | cassandra |
        """
        scale = self.k8s_apps_v1_client.read_namespaced_stateful_set_scale(
            name, namespace)
        if not scale.spec.replicas:
            scale.spec.replicas = 0
        else:
            scale.spec.replicas -= 1
        self.k8s_apps_v1_client.patch_namespaced_stateful_set(
            name, namespace, scale)

    def get_pod_names_for_stateful_set(self, name: str, namespace: str) -> list:
        """Returns expected pod names for a `Stateful Set`.
        Supposed that a `Stateful Set` manages N replicas (Kubernetes pods) which have pattern naming:
        <name_of_stateful_set>-0, <name_of_stateful_set>-1, ..., <name_of_stateful_set>-N-1.
        This behavior is default for Kubernetes `Stateful Set` but can be changed.

        Method raises an Exception if `Stateful Set` or `namespace` is not found.

        Example:
        | Get Pod Names For Stateful Set | cassandra0 | cassandra |
        """
        stateful_set = self.k8s_apps_v1_client.read_namespaced_stateful_set(
            name, namespace)
        return [f'{name}-{number}' for number in range(stateful_set.status.replicas)]

    def get_environment_variables_for_stateful_set_container(self,
                                                             name: str,
                                                             namespace: str,
                                                             container_name: str,
                                                             variable_names: list) -> dict:
        """Returns a dictionary of `Stateful Set` environment variables (key-values) for container.
        Stateful Set is found by name and namespace.
        `container_name` specifies name of docker container associated with environment variables (parameter is
        required).
        `variable_names` parameter specifies environment variable names for environment variables which should be
        returned as dictionary.

        Method raises an Exception if Stateful Set is not found.

        Example:
        | Get Environment Variables For Stateful Set Container | cassandra0 | cassandra | cassandra | <list_of_environment_variable_names> |
        """  # noqa: E501
        entity = self.get_stateful_set(name, namespace)
        return self._get_environment_variables_for_container(entity, container_name, variable_names)

    def set_environment_variables_for_stateful_set_container(self,
                                                             name: str,
                                                             namespace: str,
                                                             container_name: str,
                                                             variables_to_change: dict):
        """Changes values for given environment variables per `Stateful Set` container.
        Stateful Set is found by name and namespace.
        `container_name` specifies name of docker container associated with environment variables (parameter is
        required).
        `update_variables` parameter specifies a dictionary of variables to update. If container environment variable
        names do not contain any `update_variables` dictionary key then this `update_variables` dictionary pair is
        redundant and will be ignored.

        Method raises an Exception if Stateful Set is not found.

        Example:
        | Set Environment_Variables For Stateful Set Container | cassandra0 | cassandra | cassandra | <dictionary_of_environment_variables_to_change> |
        """  # noqa: E501
        entity = self.get_stateful_set(name, namespace)
        self._prepare_entity_with_environment_variables_for_container(
            entity, container_name, variables_to_change)
        self.k8s_apps_v1_client.patch_namespaced_stateful_set(
            name, namespace, entity)

    def get_pod(self, name: str, namespace: str):
        """Returns the particular pod configuration as JSON object.
        Method looks up the `pod` by name and namespace.

        Method raises an Exception if `Pod` or `namespace` is not found.

        Examples:
        | Get Pod | elasticsearch-0-859f48b988-2ljmx | elasticsearch-service |
        | Get Pod | cassandra1-0                     | cassandra             |
        """
        return self.k8s_core_v1_client.read_namespaced_pod(name, namespace)

    def get_pods(self, namespace: str) -> list:
        """Returns list of `Pods` by namespace/project.

        Example:
        | Get Pods | elasticsearch-service |
        """
        return self.k8s_core_v1_client.list_namespaced_pod(namespace).items

    def get_pods_by_selector(self, namespace: str, selector: dict) -> list:
        """Returns list of `Pods` from given namespace and selector.
        `selector` is a dictionary of labels. If particular pod's labels contain all labels from `selector` the `Pod`
        is added to the result list.

        Example:
        | Get Pods By Selector | elasticsearch-service | <selector_dictionary> |
        """
        return [pod for pod in self.get_pods(namespace)
                if self._do_labels_satisfy_selector(pod.metadata.labels, selector)]

    def get_pods_by_service_name(self, service_name: str, namespace: str) -> list:
        """ Returns list of `Pods` from given namespace for Service's relative `pods`.
        Method looks up `Service` by name and namespace takes its label selector and finds all matched
        Kubernetes `Pods`.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Pods By Service Name | elasticsearch | elasticsearch-service |
        """
        service_labels = self.get_service_selector(service_name, namespace)
        return self.get_pods_by_selector(namespace, service_labels)

    def get_pod_names_by_selector(self, namespace: str, selector: dict) -> list:
        """Returns list of `Pod` names from given namespace and selector.
        `selector` is a dictionary of labels. If particular pod's labels contain all labels from `selector` the `Pod`
        name is added to the result list.

        Example:
        | Get Pod Names By Selector | elasticsearch-service | <selector_dictionary> |
        """
        return [pod.metadata.name for pod in self.get_pods(namespace)
                if self._do_labels_satisfy_selector(pod.metadata.labels, selector)]

    def get_pod_names_by_service_name(self, service_name: str, namespace: str) -> list:
        """Returns list of `Pod` names from given namespace for Service's relative `pods`.
        Method looks up `Service` by name and namespace takes its label selector and finds all matched
        Kubernetes `Pods`.

        Method raises an Exception if `Service` or `namespace` is not found.

        Example:
        | Get Pod Names By Service Name | elasticsearch | elasticsearch-service |
        """
        service_labels = self.get_service_selector(service_name, namespace)
        return self.get_pod_names_by_selector(namespace, service_labels)

    def number_of_pods_in_ready_status(self, service_name: str, namespace: str) -> int:
        """
        This method returns number of pods in ready status.
        *Args:*\n
            _namespace_ (str) - OpenShift project name;\n
            _service_name_ (str) - service name;\n
        *Example:*\n
            | Number Of Pods In Ready Status | streaming-platform | streaming-service |
        """

        service_labels = self.get_service_selector(service_name, namespace)
        pods = self.get_pods_by_selector(namespace, service_labels)
        counter = 0
        for pod in pods:
            if pod.status.container_statuses[0].ready:
                counter += 1
        return counter

    def get_deployment_replicas_count(self, service: str, namespace: str, label: str = 'clusterName') -> int:
        """Returns Number of Replicas from given namespace for Service's relative `deployment`.
        Method looks up `Deployment` by service name and namespace, takes its label selector and finds all matching
        Kubernetes `Deployments`.

        Method return 0 if no `Deployment` is found.

        Example:
        | Get Deployment Replicas | streaming-platform | streaming-service |
        """
        deployment_list = self.platform_client.get_active_deployment_entities_for_service(
            namespace, service, label)
        replicas_count = 0
        for deployment in deployment_list:
            replicas_count += deployment.spec.replicas
        return replicas_count

    def get_pod_container_environment_variables_for_service(self,
                                                            namespace: str,
                                                            service: str,
                                                            container_name: str,
                                                            variable_names: list) -> dict:
        """Returns a dictionary of `Pod` names and container environment variables (key-values) from given
        namespace for Service's relative `pods`. Method looks up `Service` by name and namespace takes
        its label selector and finds all matched Kubernetes `Pods`.
        `container_name` specifies name of docker container associated with environment variables (parameter is
        required).
        `variable_names` parameter specifies environment variable names for environment variables which should be
        returned as dictionary.

        Example:
        | Get Pod Container Environment Variables For Service | elasticsearch | elasticsearch-service | elasticsearch | <list_of_variable_names> |
        """  # noqa: E501
        pods = self.get_pods_by_service_name(service, namespace)
        result = {}
        for pod in pods:
            environments = self._get_environments_for_container(
                pod.spec.containers, container_name)
            env_variables = self._get_env_variables(
                environments, variable_names)
            result[pod.metadata.labels.get('name', '')] = env_variables
        return result

    def look_up_pod_name_by_pod_ip(self, pod_ip: str, namespace: str):
        """ Returns name of `Pod` from given namespace by ip of `pod`.

        Example:
        | Look Up Pod Name By Pod Ip | 10.129.2.61 | elasticsearch-service |
        """
        pods = self.get_pods(namespace)
        for pod in pods:
            if pod.status.pod_ip == pod_ip:
                return pod.metadata.name
        return None

    def look_up_pod_ip_by_pod_name(self, pod_name: str, namespace: str):
        """ Returns IP of `Pod` from given project/namespace by name of `pod`.

        Example:
        | Look Up Pod Ip By Pod Name | kafka-1-5d569cc485-zwnpv | kafka-service |
        """
        pods = self.get_pods(namespace)
        for pod in pods:
            if pod.metadata.name in pod_name:
                return pod.status.pod_ip
        return None

    def delete_pod_by_pod_name(self, name: str, namespace: str, grace_period=0):
        """ Deletes `Pod` from given namespace by name of `pod`.

        Example:
        | Delete Pod By Pod Name | streaming-platform-1-kj8sf | streaming-platform-service |
        """
        self.k8s_core_v1_client.delete_namespaced_pod(
            namespace=namespace, name=name, grace_period_seconds=grace_period)

    def delete_pod_by_pod_ip(self, pod_ip: str, namespace: str):
        """ Deletes `Pod` from given namespace by ip of `pod`.

        Example:
        | Delete Pod By Pod Ip | 10.129.2.61 | streaming-platform-service |
        """
        pod_name = self.look_up_pod_name_by_pod_ip(pod_ip, namespace)
        if pod_name:
            self.delete_pod_by_pod_name(pod_name, namespace)

    def execute_command_in_pod(self, name: str, namespace: str, command: str,
                               container: str = "", shell: str = "/bin/bash"):
        """Executes given console command within docker container.
        `container` variable specifies name of container. It can be empty if pod contains only one container.
        The Pod is found by name and namespace. Method executes given console command within the stream and
        returns tuple of command result and error message (all of them can be empty).

        Example:
        | Execute Command In Pod | elasticsearch-0-859f48b988-2ljmx | elasticsearch | ls -la |
        | Execute Command In Pod | consul-server-1                  | consul        | ls -la | container=consul |
        | Execute Command In Pod | consul-server-1                  | consul        | ls -la | container=consul | shell=/bin/sh |
        """  # noqa: E501
        exec_cmd = [shell, '-c', command]
        response = stream(self.k8s_core_v1_client.connect_get_namespaced_pod_exec,
                          name,
                          namespace,
                          container=container,
                          command=exec_cmd,
                          stderr=True,
                          stdin=False,
                          stdout=True,
                          tty=False,
                          _preload_content=False)

        result = ""
        errors = ""
        while response.is_open():
            response.update(timeout=2)
            if response.peek_stdout():
                value = str(response.read_stdout())
                result += value
            if response.peek_stderr():
                error = response.read_stderr()
                errors += error
        return result.strip(), errors.strip()

    def get_config_map(self, name: str, namespace: str):
        """
        Returns config map by name in specified namespace.

        Example:
        | Get Config Map | elasticsearch-config-map | elasticsearch |
        """
        return self.k8s_core_v1_client.read_namespaced_config_map(name, namespace)

    def get_config_maps(self, namespace: str):
        """
        Returns config maps in specified namespace.

        Example:
        | Get Config Maps | elasticsearch |
        """
        return self.k8s_core_v1_client.list_namespaced_config_map(namespace)

    def create_config_map_from_file(self, namespace, file_path):
        """
        Creates config map by specified file path in namespace.
        The file must be in the yaml format.

        Example:
        | Create Config Map From File | elasticsearch | <path>/config.yaml |
        """
        body = self._parse_yaml_from_file(file_path)
        return self.k8s_core_v1_client.create_namespaced_config_map(namespace, body)

    def delete_config_map_by_name(self, name: str, namespace: str):
        """
        Delete config map by name in specified namespace.

        Example:
        | Delete Config Map By Name | elasticsearch-config-map | elasticsearch |
        """
        return self.k8s_core_v1_client.delete_namespaced_config_map(name, namespace)

    def get_secret(self, name: str, namespace: str):
        """
        Returns secret in specified namespace.

        Example:
        | Get Secret | elasticsearch-secret | elasticsearch |
        """
        return self.k8s_core_v1_client.read_namespaced_secret(name, namespace)

    def get_secrets(self, namespace: str):
        """
        Returns secrets in specified namespace.

        Example:
        | Get Secrets | elasticsearch |
        """
        return self.k8s_core_v1_client.list_namespaced_secret(namespace)

    def create_secret(self, namespace, body):
        """Create secret in specified namespace.

        :param namespace: the secret's namespace
        :param body: the JSON schema of the Secret to create.

        Example:
        | Create Secret | elasticsearch | secret_body |
        """
        return self.k8s_core_v1_client.create_namespaced_secret(namespace, body)

    def patch_secret(self, name, namespace, body):
        """Update secret in specified namespace.

        :param name: the secret's name
        :param namespace: the secret's namespace
        :param body: the JSON schema of the Secret to create.

        Example:
        | Patch Secret | opensearch-secret | opensearch | secret_body |
        """
        return self.k8s_core_v1_client.patch_namespaced_secret(name, namespace, body)

    def delete_secret_by_name(self, name: str, namespace: str):
        """
        Delete secret by name in specified namespace.

        Example:
        | Delete Secret By Name | elasticsearch-secret | elasticsearch |
        """
        return self.k8s_core_v1_client.delete_namespaced_secret(name, namespace)

    def get_replica_sets(self, namespace: str):
        """
        Returns replica sets in specified namespace.

        Example:
        | Get Replica Sets | elasticsearch |
        """
        return self.k8s_apps_v1_client.list_namespaced_replica_set(namespace)

    def get_replica_set(self, name: str, namespace: str):
        """
        Returns replica set by replica set name in specified namespace.

        Example:
        | Get Replica Set | elasticsearch-replica-set | elasticsearch |
        """
        return self.k8s_apps_v1_client.read_namespaced_replica_set(name, namespace)

    def get_image(self, resource, container_name):
        """
        Returns image from resource configuration by container name in specified namespace.
        """
        if len(resource.spec.template.spec.containers) > 1 and container_name is not None:
            for container in resource.spec.template.spec.containers:
                if container.name == container_name:
                    return container.image
        elif len(resource.spec.template.spec.containers) == 1:
            return resource.spec.template.spec.containers[0].image
        return None

    def get_resource_image(self, resource_type: str, resource_name: str, namespace: str, resource_container_name=None):
        """
        Identifies the resource type and return image for the specified resource by the name
        of the resource and container in the specified namespace.
        """
        if resource_type == 'daemonset':
            daemon_set = self.get_daemon_set(resource_name, namespace)
            return self.get_image(daemon_set, resource_container_name)
        elif resource_type == 'deployment':
            deployment = self.get_deployment_entity(resource_name, namespace)
            return self.get_image(deployment, resource_container_name)
        elif resource_type == 'statefulset':
            stateful_set = self.get_stateful_set(resource_name, namespace)
            return self.get_image(stateful_set, resource_container_name)
        else:
            raise Exception(
                f'The type [{resource_type}] is not supported yet.')

    def get_dd_images_from_config_map(self, config_map_name, namespace):
        config_map = self.get_config_map(config_map_name, namespace)
        config_map_yaml = (config_map.to_dict())
        cm = config_map_yaml["data"]["dd_images"]
        if cm:
            return cm
        else:
            return None

    def get_pod_logs(self, pod_name: str, namespace: str, container_name: str = None, tail_lines: int = 100) -> str:
        """
        Returns logs from a given pod in the specified namespace and container.
        """

        return self.k8s_core_v1_client.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container_name,
            tail_lines=tail_lines
        )

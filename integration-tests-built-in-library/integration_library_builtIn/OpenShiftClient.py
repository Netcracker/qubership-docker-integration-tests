from openshift.dynamic import DynamicClient


class OpenShiftClient(object):
    def __init__(self, api_client):
        self.api_client = api_client
        self.dyn_client = DynamicClient(api_client)
        self._patch_scale_dict = {'spec': {'replicas': 1}}

    def get_deployment_entity(self, name: str, namespace: str):
        return self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig').get(namespace=namespace, name=name)

    def get_deployment_entities(self, namespace: str):
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        return deployment_configs.get(namespace=namespace).items

    def get_deployment_entity_names_for_service(self, namespace: str, service: str, label: str = 'clusterName') -> list:
        deployment_configs = self.get_deployment_entities(namespace)
        deployment_config_names = []
        for deployment in deployment_configs:
            if deployment.spec.template.metadata.labels.get(label, '') == service:
                deployment_config_names.append(deployment.metadata.name)
        return deployment_config_names

    def get_inactive_deployment_entities_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> list:
        deployment_configs = self.get_deployment_entities(namespace)
        inactive_dc = []

        for dc in deployment_configs:
            if dc.spec.template.metadata.labels.get(label, '') == service:
                    if dc.status.availableReplicas == 0 or not dc.status.replicas:
                        inactive_dc.append(dc)
        return inactive_dc

    def get_inactive_deployment_entities_names_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> list:
        inactive_dc = self.get_inactive_deployment_entities_for_service(namespace, service, label)
        inactive_dc_names = []
        for deployment in inactive_dc:
            inactive_dc_names.append(deployment.metadata.name)
        return inactive_dc_names

    def get_inactive_deployment_entities_count_for_service(self,
                                                           namespace: str,
                                                           service: str,
                                                           label: str = 'clusterName') -> int:
        deployment_configs = self.get_deployment_entities(namespace)
        if not deployment_configs:
            return 0
        return len(self.get_inactive_deployment_entities_for_service(namespace, service, label))


    def get_first_deployment_entity_name_for_service(self,
                                                     namespace: str,
                                                     service: str,
                                                     label: str = 'clusterName') -> str:
        deployment_configs = self.get_deployment_entities(namespace)
        for dc in deployment_configs:
            if dc.spec.template.metadata.labels.get(label, '') == service:
                return dc.metadata.name
        return None

    def get_active_deployment_entities_for_service(self,
                                                   namespace: str,
                                                   service: str,
                                                   label: str = 'clusterName') -> list:
        deployment_configs = self.get_deployment_entities(namespace)
        active_dc = []

        for dc in deployment_configs:
            if dc.spec.template.metadata.labels.get(label, '') == service \
                    and not dc.status.unavailableReplicas \
                    and dc.status.availableReplicas != 0:
                active_dc.append(dc)
        return active_dc

    def get_active_deployment_entities_names_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str ='clusterName') -> list:

        active_dc = self.get_active_deployment_entities_for_service(namespace, service, label)
        active_dc_names = []
        for deployment in active_dc:
            active_dc_names.append(deployment.metadata.name)
        return active_dc_names

    def get_active_deployment_entities_count_for_service(self,
                                                         namespace: str,
                                                         service: str,
                                                         label: str = 'clusterName') -> int:
        deployment_configs = self.get_deployment_entities(namespace)
        if not deployment_configs:
            return 0
        return len(self.get_active_deployment_entities_for_service(namespace, service, label))

    def get_deployment_entities_count_for_service(self, namespace: str, service: str, label: str = 'clusterName'):
        return len(self.get_deployment_entity_names_for_service(namespace, service, label))

    def set_replicas_for_deployment_entity(self, name: str, namespace: str, replicas: int = 1):
        self._patch_scale_dict['spec']['replicas'] = replicas
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        deployment_configs.patch(body=self._patch_scale_dict, name=name, namespace=namespace)

    def scale_up_deployment_entity(self, name: str, namespace: str):
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        replicas = None
        dc = deployment_configs.get(name, namespace)
        if dc:
            replicas = dc.spec.replicas
        if replicas is None:
            replicas = 1
        else:
            replicas += 1
        self._patch_scale_dict['spec']['replicas'] = replicas
        deployment_configs.patch(body=self._patch_scale_dict, name=name, namespace=namespace)

    def scale_down_deployment_entity(self, name: str, namespace: str):
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        replicas = None
        dc = deployment_configs.get(name, namespace)
        if dc:
            replicas = dc.spec.replicas
        if replicas:
            replicas -= 1
            self._patch_scale_dict['spec']['replicas'] = replicas
            deployment_configs.patch(body=self._patch_scale_dict, name=name, namespace=namespace)

    def get_deployment_entity_pod_selector_labels(self, name: str, namespace: str) -> dict:
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        return deployment_configs.get(name=name, namespace=namespace).spec.selector

    # TODO: check that body is dictionary
    def patch_namespaced_deployment_entity(self, name: str, namespace: str, body):
        deployment_configs = self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig')
        deployment_configs.patch(name=name, namespace=namespace, body=body)

    def get_deployment_entity_ready_replicas(self, deployment):
        return deployment.status.readyReplicas

    def get_deployment_entity_unavailable_replicas(self, deployment):
        return deployment.status.unavailableReplicas

    def create_deployment_entity(self, body, namespace: str):
        return self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig') \
            .create(body=body, namespace=namespace)

    def delete_deployment_entity(self, name: str, namespace: str):
        return self.dyn_client.resources.get(api_version='apps.openshift.io/v1', kind='DeploymentConfig') \
            .delete(name=name, namespace=namespace)

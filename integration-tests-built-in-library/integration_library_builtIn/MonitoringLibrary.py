import json

import requests
import urllib3

from PlatformLibrary import PlatformLibrary

from requests.auth import HTTPBasicAuth

from robot.libraries.BuiltIn import BuiltIn

class MonitoringLibrary(object):
    """This Robot Framework library provides access to the Prometheus API for working with rules and the ability to
    perform operations with GrafanaDashboards Custom Resources like Kubernetes entities.

    To access the Prometheus when using the library, you need to specify the parameter `host` specifying the protocol,
    host and port of Prometheus. By default MonitoringLibrary is imported without this parameter.
    To perform operations only on GrafanaDashboard Custom Resources, the library can be imported without specifying the
    `host`.

    These are examples of import library with Prometheus host initialization.

    | Library | MonitoringLibrary | host=http://${PROMETHEUS_HOST}:${PROMETHEUS_PORT} |
    | Library | MonitoringLibrary |
    """

    def __init__(self, host=None, username=None, password=None):

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self._host = host
        self._api_rules_url = f'{host}/api/v1/rules'
        self._headers = {'Content-Type': 'application/json'}
        self._auth = HTTPBasicAuth(username, password)
        self.k8s_lib = PlatformLibrary()

    def get_alert_status(self, alert_name, namespace):
        """Returns status of specified alert name. Possible return values: inactive, firing, pending

        Examples:
        | Get Alert Status | Elasticsearch_Is_Down_Alarm | elasticsearch-service
        """
        response = requests.get(self._api_rules_url, auth=self._auth)
        json_content = json.loads(response.text)
        groups = json_content["data"]["groups"]
        namespace_in_query = f'namespace="{namespace}"'
        for group in groups:
            for rule in group["rules"]:
                if rule['name'] == alert_name:
                    namespace_label = rule['labels'].get('namespace')
                    if namespace_label == namespace:
                        return rule["state"]
                    elif namespace_label is None and namespace_in_query in rule["query"]:
                        BuiltIn().run_keyword('log to console',
                                              f"Warning! There is no namespace label in {alert_name} alert")
                        return rule["state"]
        return None

    def get_metric_values(self, metric_name: str):
        _api_query_url = f'{self._host}/api/v1/query?query={metric_name}'
        response = requests.get(_api_query_url, auth=self._auth)
        json_content = json.loads(response.text)
        return json_content["data"]

    def get_full_metric_values(self, metric_name: str):
        """Returns all values for specified metric name.

        Examples:
        | Get Full Metric Values | kafka_kafka_Threading_ThreadCount
        """
        data = self.get_metric_values(metric_name)
        all_values = []
        for res in data["result"]:
            all_values.append(res["value"][1])
        return all_values

    def get_last_metric_value(self, metric_name: str):
        """Returns last value for specified metric name.

        Examples:
        | Get Last Metric Value | kafka_kafka_Threading_ThreadCount
        """
        data = self.get_metric_values(metric_name)
        return data["result"][0]["value"][1]

    def get_dashboard_in_namespace(self, namespace, name):
        """Returns Kubernetes 'GrafanaDashboard' custom object with body configuration as JSON object in project/namespace.

        :param namespace: namespace of existing GrafanaDashboard
        :param name: the name of GrafanaDashboard to return

        Example:
        | Get Dashboard In Namespace | prometheus-operator | grafanadashboard_name |
        """
        return self.k8s_lib.get_namespaced_custom_object(group='integreatly.org', version='v1alpha1',
                                                         namespace=namespace, plural='grafanadashboards', name=name)

    def create_dashboard_in_namespace(self, namespace, body):
        """Method of creating Kubernetes 'GrafanaDashboard' custom object with body configuration as JSON object in project/namespace.

        :param namespace: namespace where GrafanaDashboard to be created
        :param body: JSON object for creating GrafanaDashboard

        Example:
        | Create Dashboard In Namespace | prometheus-operator | grafandashboard_body |
        """
        return self.k8s_lib.create_namespaced_custom_object(group='integreatly.org', version='v1alpha1',
                                                            namespace=namespace, plural='grafanadashboards', body=body)

    def delete_dashboard_in_namespace(self, namespace, name):
        """Deletes Kubernetes 'GrafanaDashboard' custom object in project/namespace.

        :param namespace: namespace of existing GrafanaDashboard
        :param name: the name of GrafanaDashboard to delete

        Example:
        | Delete Dashboard In Namespace | prometheus-operator | grafanadashboard_name |
        """
        return self.k8s_lib.delete_namespaced_custom_object(group='integreatly.org', version='v1alpha1',
                                                            namespace=namespace, plural='grafanadashboards', name=name)

    def patch_dashboard_in_namespace(self, namespace, name, body):
        """Patches Kubernetes 'GrafanaDashboard' custom object with body configuration as JSON object in project/namespace.

        :param namespace: namespace of existing GrafanaDashboard
        :param name: the name of GrafanaDashboard to patch
        :param body: JSON object to patch GrafanaDashboard

        Example:
        | Patch Dashboard In Namespace | prometheus-operator | test_dashboard | grafanadashboard_body |
        """
        return self.k8s_lib.patch_namespaced_custom_object(group='integreatly.org', version='v1alpha1',
                                                           namespace=namespace, plural='grafanadashboards', name=name,
                                                           body=body)

    def replace_dashboard_in_namespace(self, namespace, name, body):
        """Method for replacing Kubernetes 'GrafanaDashboard' custom object with body configuration as JSON object in project/namespace.

        :param namespace: namespace of existing GrafanaDashboard
        :param name: the name of GrafanaDashboard to replace
        :param body: JSON object for replace GrafanaDashboard

        Example:
        | Replace Dashboard In Namespace | prometheus-operator | test_dashboard | grafanadashboard_body |
        """
        return self.k8s_lib.replace_namespaced_custom_object(group='integreatly.org', version='v1alpha1',
                                                             namespace=namespace, plural='grafanadashboards', name=name,
                                                             body=body)

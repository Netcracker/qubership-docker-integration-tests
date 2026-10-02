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

"""Tests for MonitoringLibrary against a stubbed Prometheus API and a mocked PlatformLibrary."""

import base64
from unittest.mock import patch

import MonitoringLibrary as monitoring_module
import pytest
import responses

PROMETHEUS = "http://prometheus.test:9090"


@pytest.fixture
def platform_library():
    with patch.object(monitoring_module, "PlatformLibrary") as platform_library_class:
        yield platform_library_class.return_value


@pytest.fixture
def library(platform_library):
    return monitoring_module.MonitoringLibrary(host=PROMETHEUS, username="user", password="password")


@pytest.fixture
def prometheus():
    with responses.RequestsMock() as mock:
        yield mock


def rule(name, state, labels=None, query="up == 0"):
    return {"name": name, "state": state, "labels": labels or {}, "query": query}


def stub_rules(prometheus, *rules):
    prometheus.get(f"{PROMETHEUS}/api/v1/rules", json={"data": {"groups": [{"rules": list(rules)}]}})


class TestGetAlertStatus:
    def test_returns_state_of_alert_in_namespace(self, library, prometheus):
        stub_rules(
            prometheus,
            rule("KafkaIsDown", "inactive", {"namespace": "other"}),
            rule("KafkaIsDown", "firing", {"namespace": "kafka"}),
        )

        assert library.get_alert_status("KafkaIsDown", "kafka") == "firing"

        expected = "Basic " + base64.b64encode(b"user:password").decode()
        assert prometheus.calls[0].request.headers["Authorization"] == expected

    def test_matches_namespace_in_query_when_label_is_missing(self, library, prometheus):
        stub_rules(prometheus, rule("KafkaIsDown", "pending", query='up{namespace="kafka"} == 0'))

        with patch.object(monitoring_module, "BuiltIn") as built_in:
            assert library.get_alert_status("KafkaIsDown", "kafka") == "pending"

        built_in.return_value.run_keyword.assert_called_once()

    def test_returns_none_for_unknown_alert(self, library, prometheus):
        stub_rules(prometheus, rule("ZooKeeperIsDown", "firing", {"namespace": "kafka"}))

        assert library.get_alert_status("KafkaIsDown", "kafka") is None


class TestMetrics:
    @pytest.fixture(autouse=True)
    def metric(self, prometheus):
        prometheus.get(
            f"{PROMETHEUS}/api/v1/query",
            json={
                "data": {
                    "result": [
                        {"metric": {"pod": "kafka-1"}, "value": [1700000000, "12"]},
                        {"metric": {"pod": "kafka-2"}, "value": [1700000000, "15"]},
                    ]
                }
            },
        )

    def test_full_metric_values(self, library, prometheus):
        assert library.get_full_metric_values("kafka_threads") == ["12", "15"]
        assert prometheus.calls[0].request.params == {"query": "kafka_threads"}

    def test_last_metric_value(self, library):
        assert library.get_last_metric_value("kafka_threads") == "12"


class TestGrafanaDashboards:
    DASHBOARD = {
        "group": "integreatly.org",
        "version": "v1alpha1",
        "namespace": "monitoring",
        "plural": "grafanadashboards",
    }

    def test_get(self, library, platform_library):
        library.get_dashboard_in_namespace("monitoring", "kafka")
        platform_library.get_namespaced_custom_object.assert_called_once_with(**self.DASHBOARD, name="kafka")

    def test_create(self, library, platform_library):
        library.create_dashboard_in_namespace("monitoring", {"spec": {}})
        platform_library.create_namespaced_custom_object.assert_called_once_with(**self.DASHBOARD, body={"spec": {}})

    def test_delete(self, library, platform_library):
        library.delete_dashboard_in_namespace("monitoring", "kafka")
        platform_library.delete_namespaced_custom_object.assert_called_once_with(**self.DASHBOARD, name="kafka")

    def test_patch(self, library, platform_library):
        library.patch_dashboard_in_namespace("monitoring", "kafka", {"spec": {}})
        platform_library.patch_namespaced_custom_object.assert_called_once_with(
            **self.DASHBOARD, name="kafka", body={"spec": {}}
        )

    def test_replace(self, library, platform_library):
        library.replace_dashboard_in_namespace("monitoring", "kafka", {"spec": {}})
        platform_library.replace_namespaced_custom_object.assert_called_once_with(
            **self.DASHBOARD, name="kafka", body={"spec": {}}
        )

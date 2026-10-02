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

"""Tests for scripts/write_status.py, which writes the integration tests status condition to a custom resource."""

from unittest.mock import patch

import pytest
import write_status
from write_status import (
    Condition,
    ConditionStatus,
    ConditionType,
    CustomResourceStatusResolver,
)

STATUS_ENV = [
    "STATUS_CUSTOM_RESOURCE_PATH",
    "STATUS_CUSTOM_RESOURCE_GROUP",
    "STATUS_CUSTOM_RESOURCE_VERSION",
    "STATUS_CUSTOM_RESOURCE_NAMESPACE",
    "STATUS_CUSTOM_RESOURCE_PLURAL",
    "STATUS_CUSTOM_RESOURCE_NAME",
    "ONLY_INTEGRATION_TESTS",
    "IS_SHORT_STATUS_MESSAGE",
    "IS_STATUS_BOOLEAN",
]

PASSED_RESULT = "Main Test Suite: Tests\t|\tPassed: 2\t|\tFailed: 0\nSuite details\nRESULT: TESTS PASSED\n"
FAILED_RESULT = "Main Test Suite: Tests\t|\tPassed: 1\t|\tFailed: 1\nSuite details\nRESULT: TESTS FAILED\n"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in STATUS_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def result_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "output").mkdir()

    def write(content):
        (tmp_path / "output" / "result.txt").write_text(content)

    return write


def generate(**kwargs):
    condition = Condition(**kwargs)
    condition.generate_condition_state()
    return condition


class TestCondition:
    def test_in_progress(self):
        condition = generate(is_in_progress=True)

        assert condition.message == "Service in progress"
        assert condition.type == ConditionType.IN_PROGRESS
        assert condition.status == ConditionStatus.FALSE

    def test_passed_run_is_ready_with_short_message(self, result_file):
        result_file(PASSED_RESULT)

        condition = generate()

        assert condition.status == ConditionStatus.TRUE
        assert condition.type == ConditionType.READY
        assert condition.message == "Main Test Suite: Tests  |  Passed: 2  |  Failed: 0"

    def test_passed_run_is_successful_when_only_integration_tests(self, result_file, monkeypatch):
        result_file(PASSED_RESULT)
        monkeypatch.setenv("ONLY_INTEGRATION_TESTS", "True")

        assert generate().type == ConditionType.SUCCESSFUL

    def test_failed_run(self, result_file):
        result_file(FAILED_RESULT)

        condition = generate()

        assert condition.status == ConditionStatus.FALSE
        assert condition.type == ConditionType.FAILED

    def test_full_message_when_short_message_is_disabled(self, result_file, monkeypatch):
        result_file(FAILED_RESULT)
        monkeypatch.setenv("IS_SHORT_STATUS_MESSAGE", "false")

        assert generate().message == FAILED_RESULT

    def test_condition_body(self):
        body = Condition(message="msg", status=ConditionStatus.TRUE, type=ConditionType.READY).get_condition_body()

        assert body["message"] == "msg"
        assert body["reason"] == "IntegrationTestsExecutionStatus"
        assert body["status"] == "True"
        assert body["type"] == "Ready"
        assert body["lastTransitionTime"].endswith("Z")

    @pytest.mark.parametrize("status, expected", [(ConditionStatus.TRUE, True), (ConditionStatus.FALSE, False)])
    def test_boolean_status(self, monkeypatch, status, expected):
        monkeypatch.setenv("IS_STATUS_BOOLEAN", "true")

        assert Condition(status=status).get_condition_body()["status"] is expected


class TestCustomResourceStatusResolver:
    def test_reads_custom_resource_from_separate_variables(self, monkeypatch):
        for suffix, value in [
            ("GROUP", "qubership.org"),
            ("VERSION", "v1"),
            ("NAMESPACE", "kafka"),
            ("PLURAL", "kafkaservices"),
            ("NAME", "kafka"),
        ]:
            monkeypatch.setenv(f"STATUS_CUSTOM_RESOURCE_{suffix}", value)

        resolver = CustomResourceStatusResolver()

        assert (resolver.group, resolver.version, resolver.namespace, resolver.plural, resolver.name) == (
            "qubership.org",
            "v1",
            "kafka",
            "kafkaservices",
            "kafka",
        )

    def test_reads_custom_resource_from_path(self, monkeypatch):
        monkeypatch.setenv("STATUS_CUSTOM_RESOURCE_PATH", "qubership.org/v1/kafka/kafkaservices/kafka")

        resolver = CustomResourceStatusResolver()

        assert (resolver.group, resolver.version, resolver.namespace, resolver.plural, resolver.name) == (
            "qubership.org",
            "v1",
            "kafka",
            "kafkaservices",
            "kafka",
        )

    def test_rejects_path_with_wrong_number_of_parts(self, monkeypatch):
        monkeypatch.setenv("STATUS_CUSTOM_RESOURCE_PATH", "qubership.org/v1/kafka")

        with pytest.raises(Exception, match="exactly five parts, 3 given"):
            CustomResourceStatusResolver()

    def test_rejects_missing_attributes(self, monkeypatch):
        monkeypatch.setenv("STATUS_CUSTOM_RESOURCE_GROUP", "qubership.org")

        with pytest.raises(Exception, match="version,namespace,plural,name attributes must not be empty"):
            CustomResourceStatusResolver().check_cr_path()


class TestStatusUpdate:
    CONDITION = {"reason": "IntegrationTestsExecutionStatus", "type": "Ready", "status": "True"}
    OTHER_CONDITION = {"reason": "DeploymentStatus", "type": "Ready", "status": "True"}

    @pytest.fixture
    def platform_library(self, monkeypatch):
        monkeypatch.setenv("STATUS_CUSTOM_RESOURCE_PATH", "qubership.org/v1/kafka/kafkaservices/kafka")
        with patch.object(write_status, "PlatformLibrary") as platform_library_class:
            yield platform_library_class.return_value

    def update(self, platform_library, current_object):
        platform_library.get_namespaced_custom_object_status.return_value = current_object
        CustomResourceStatusResolver().update_custom_resource_status_condition(self.CONDITION)
        args = platform_library.custom_objects_api.patch_namespaced_custom_object_status.call_args.args
        assert args[:5] == ("qubership.org", "v1", "kafka", "kafkaservices", "kafka")
        return args[5]["status"]["conditions"]

    def test_adds_status_when_custom_resource_has_none(self, platform_library):
        assert self.update(platform_library, {}) == [self.CONDITION]

    def test_adds_conditions_when_status_has_none(self, platform_library):
        assert self.update(platform_library, {"status": {"phase": "Running"}}) == [self.CONDITION]

    def test_appends_condition_next_to_other_conditions(self, platform_library):
        conditions = self.update(platform_library, {"status": {"conditions": [self.OTHER_CONDITION]}})

        assert conditions == [self.OTHER_CONDITION, self.CONDITION]

    def test_replaces_previous_integration_tests_condition(self, platform_library):
        previous = {"reason": "IntegrationTestsExecutionStatus", "type": "In Progress", "status": "False"}

        conditions = self.update(platform_library, {"status": {"conditions": [self.OTHER_CONDITION, previous]}})

        assert conditions == [self.OTHER_CONDITION, self.CONDITION]

from PlatformLibrary import PlatformLibrary
from datetime import datetime
from enum import Enum
import os
import sys
import re

class CustomResourceStatusResolver:
    def __init__(self, **kwargs):
        self.path = os.getenv("STATUS_CUSTOM_RESOURCE_PATH")
        if self.path is None:
            self.group = os.getenv("STATUS_CUSTOM_RESOURCE_GROUP")
            self.version = os.getenv("STATUS_CUSTOM_RESOURCE_VERSION")
            self.namespace = os.getenv("STATUS_CUSTOM_RESOURCE_NAMESPACE")
            self.plural = os.getenv("STATUS_CUSTOM_RESOURCE_PLURAL")
            self.name = os.getenv("STATUS_CUSTOM_RESOURCE_NAME")
        else:
            self.resolve_custom_resource_by_path()

    def resolve_custom_resource_by_path(self):
        parts = self.path.split("/")
        if len(parts) != 5:
            raise Exception(f'Path to custom resource must contain exactly five parts, {len(parts)} given')
        self.group = parts[0]
        self.version = parts[1]
        self.namespace = parts[2]
        self.plural = parts[3]
        self.name = parts[4]

    def check_cr_path(self):
        errors = []
        for attr, value in self.__dict__.items():
            if attr != "path" and not value:
                errors.append(attr)
        if errors:
            raise Exception(f'{",".join(errors)} attribute{"s" if len(errors) > 1 else ""} must not be empty to find '
                            f'custom resource for status update')

    def update_custom_resource_status_condition(self, condition):
        self.check_cr_path()
        client = PlatformLibrary(managed_by_operator="true")
        status_obj = client.get_namespaced_custom_object_status(self.group,
                                                                self.version,
                                                                self.namespace,
                                                                self.plural,
                                                                self.name)
        status = status_obj.get('status')
        conditions = []
        if status is not None:
            conditions = status.get('conditions')
        else:
            status = {}
            status_obj['status'] = status
        is_presented = False
        for i, con in enumerate(conditions):
            if con['reason'] == "IntegrationTestsExecutionStatus":
                conditions[i] = condition
                is_presented = True
                break
        if not is_presented:
            conditions.append(condition)

        status['conditions'] = conditions
        client.custom_objects_api.patch_namespaced_custom_object_status(self.group,
                                                                        self.version,
                                                                        self.namespace,
                                                                        self.plural,
                                                                        self.name,
                                                                        status_obj)


class ConditionType(Enum):
    SUCCESSFUL = "Successful"
    FAILED = "Failed"
    IN_PROGRESS = 'In Progress'
    READY = 'Ready'


class ConditionStatus(Enum):
    TRUE = "True"
    FALSE = "False"
    UNKNOWN = "Unknown"


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

class Condition:
    def __init__(self,
                 is_in_progress: bool = False,
                 message: str = None,
                 reason: str = None,
                 status: ConditionStatus = None,
                 type: ConditionType = None):
        self.is_in_progress = is_in_progress
        self.message = message
        self.reason = reason if reason is not None else "IntegrationTestsExecutionStatus"
        self.status = status if status is not None else ConditionStatus.UNKNOWN
        self.type = type if type is not None else ConditionType.READY

    def get_condition_body(self):
        status_value = self.status.value
        if str2bool(os.getenv("IS_STATUS_BOOLEAN", "false")):
            status_value = str2bool(status_value)
        return {"message": self.message,
                "reason": self.reason,
                "status": status_value,
                "type": self.type.value,
                "lastTransitionTime": datetime.utcnow().isoformat()[:-3]+'Z'}

    def generate_condition_state(self):
        if self.is_in_progress:
            self.generate_in_progress_condition_state()
            return
        with open('./output/result.txt', 'r') as file:
            self.message = file.read()
            if "RESULT: TESTS PASSED" in self.message:
                self.status = ConditionStatus.TRUE
                if os.getenv("ONLY_INTEGRATION_TESTS") and os.getenv("ONLY_INTEGRATION_TESTS").lower() == "true":
                    self.type = ConditionType.SUCCESSFUL
                else:
                    self.type = ConditionType.READY
            else:
                self.status = ConditionStatus.FALSE
                self.type = ConditionType.FAILED
            if os.getenv("IS_SHORT_STATUS_MESSAGE", "true").lower() == "true":
                result_str = self.message.split("\n")[0]
                self.message = re.sub(r'\t', "  ", result_str)

    def generate_in_progress_condition_state(self):
        self.message = "Service in progress"
        self.type = ConditionType.IN_PROGRESS
        self.status = ConditionStatus.FALSE


if __name__ == '__main__':
    argv = sys.argv[1:]
    is_in_progress = False if len(argv) < 1 or argv[0] != "in_progress" else True

    condition = Condition(is_in_progress=is_in_progress)
    condition.generate_condition_state()
    condition_body = condition.get_condition_body()
    status_resolver = CustomResourceStatusResolver()
    status_resolver.update_custom_resource_status_condition(condition_body)

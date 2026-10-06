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

"""Guards the keyword signatures that downstream .robot suites call (see "Compatibility Rules" in AGENTS.md).

keyword_signatures.json records every public method and library import argument. A keyword must not be
removed or renamed, and existing arguments must keep their name, order, kind, and default. A new argument
must come after the existing ones and have a default.

After adding a keyword or an optional argument, refresh the snapshot and commit it:

    UPDATE_KEYWORD_SIGNATURES=1 pytest library/tests/test_keyword_signatures.py
"""

import importlib
import inspect
import json
import os
from pathlib import Path

import pytest

SNAPSHOT = Path(__file__).parent / "data" / "keyword_signatures.json"
LIBRARIES = ["PlatformLibrary", "MonitoringLibrary", "OAuthLibrary", "S3BackupLibrary"]


def describe(function):
    parameters = list(inspect.signature(function).parameters.values())[1:]  # skip self
    return [
        {
            "name": parameter.name,
            "kind": parameter.kind.name,
            **({} if parameter.default is inspect.Parameter.empty else {"default": repr(parameter.default)}),
        }
        for parameter in parameters
    ]


def current_signatures():
    signatures = {}
    for library in LIBRARIES:
        cls = getattr(importlib.import_module(library), library)
        keywords = {"__init__": describe(cls.__init__)}
        for name, member in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith("_"):
                keywords[name] = describe(member)
        signatures[library] = keywords
    return signatures


def compatibility_errors(recorded, current):
    errors = []
    for library, keywords in recorded.items():
        for keyword, old_parameters in keywords.items():
            where = f"{library}.{keyword}"
            new_parameters = current.get(library, {}).get(keyword)
            if new_parameters is None:
                errors.append(f"{where}: removed or renamed")
                continue
            for position, old in enumerate(old_parameters):
                new = new_parameters[position] if position < len(new_parameters) else None
                if new != old:
                    errors.append(f"{where}: argument {position + 1} changed from {old} to {new}")
            first_added = len(old_parameters)
            for added in new_parameters[first_added:]:
                if "default" not in added and not added["kind"].startswith("VAR_"):
                    errors.append(f"{where}: new argument '{added['name']}' has no default")
    return errors


def test_keyword_signatures_stay_backward_compatible():
    current = current_signatures()
    if os.getenv("UPDATE_KEYWORD_SIGNATURES"):
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    recorded = json.loads(SNAPSHOT.read_text())

    errors = compatibility_errors(recorded, current)

    assert not errors, "Incompatible keyword changes break downstream suites:\n" + "\n".join(errors)
    assert current == recorded, (
        "Keywords were added. Refresh the snapshot with UPDATE_KEYWORD_SIGNATURES=1 and commit it."
    )


@pytest.mark.parametrize(
    "change, expected",
    [
        ({"PlatformLibrary": {}}, "PlatformLibrary.get_pods: removed or renamed"),
        (
            {"PlatformLibrary": {"get_pods": [{"name": "ns", "kind": "POSITIONAL_OR_KEYWORD"}]}},
            "PlatformLibrary.get_pods: argument 1 changed",
        ),
        (
            {
                "PlatformLibrary": {
                    "get_pods": [
                        {"name": "namespace", "kind": "POSITIONAL_OR_KEYWORD"},
                        {"name": "label", "kind": "POSITIONAL_OR_KEYWORD"},
                    ]
                }
            },
            "PlatformLibrary.get_pods: new argument 'label' has no default",
        ),
    ],
)
def test_incompatible_changes_are_reported(change, expected):
    recorded = {"PlatformLibrary": {"get_pods": [{"name": "namespace", "kind": "POSITIONAL_OR_KEYWORD"}]}}

    errors = compatibility_errors(recorded, change)

    assert any(error.startswith(expected) for error in errors), errors

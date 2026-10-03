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

"""Tests for scripts/robot_tags_resolver.py.

The script resolves tags at import time, so each test runs it the way docker-entrypoint.sh does: as a
separate process in a directory that contains ./tests. The entrypoint splits the output on ';' into the
robot -e argument and a description of the excluded tags.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "robot_tags_resolver.py"


def write_exclusion(directory: Path, body: str):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "tags_exclusion.py").write_text(f"def get_excluded_tags(environ):\n    {body}\n")


def resolve(cwd: Path, **env):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=True,
    )
    exclude_argument, description, trailing = result.stdout.rstrip("\n").split(";")
    assert trailing == ""
    return exclude_argument, description


def excluded_tags(exclude_argument: str) -> set:
    assert exclude_argument.startswith("-e ")
    return set(exclude_argument.removeprefix("-e ").split("OR"))


def test_no_tests_directory_excludes_nothing(tmp_path):
    assert resolve(tmp_path) == ("", "")


def test_tests_directory_without_exclusion_modules_excludes_nothing(tmp_path):
    (tmp_path / "tests" / "suite").mkdir(parents=True)
    assert resolve(tmp_path) == ("", "")


def test_list_of_tags_is_excluded_without_description(tmp_path):
    write_exclusion(tmp_path / "tests", "return ['ha', 'backup']")

    exclude_argument, description = resolve(tmp_path)

    assert excluded_tags(exclude_argument) == {"ha", "backup"}
    assert description == ""


def test_dict_of_tags_is_excluded_with_reasons(tmp_path):
    write_exclusion(tmp_path / "tests", "return {'ha': 'OS_URL is not set'}")

    exclude_argument, description = resolve(tmp_path)

    assert exclude_argument == "-e ha"
    assert description == "The following tags will be excluded with provided reason\nha: OS_URL is not set"


def test_modules_in_nested_directories_are_merged(tmp_path):
    write_exclusion(tmp_path / "tests" / "kafka" / "ha", "return {'ha': 'no ZooKeeper'}")
    write_exclusion(tmp_path / "tests" / "kafka" / "backup", "return ['backup', 'ha']")

    exclude_argument, description = resolve(tmp_path)

    assert excluded_tags(exclude_argument) == {"ha", "backup"}
    assert "ha: no ZooKeeper" in description


def test_module_receives_the_process_environment(tmp_path):
    write_exclusion(tmp_path / "tests", "return ['acl'] if environ.get('EXTERNAL_KAFKA') else []")

    assert resolve(tmp_path) == ("", "")
    assert excluded_tags(resolve(tmp_path, EXTERNAL_KAFKA="true")[0]) == {"acl"}

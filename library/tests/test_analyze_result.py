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

"""Tests for scripts/analyze_result.py.

The script reads ./output/output.xml through the Robot Framework result API, so the tests produce that
file with the installed Robot Framework. A Robot Framework update that changes the result model fails
here before it reaches the image.
"""

import io
import subprocess
import sys
from pathlib import Path

import robot

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "analyze_result.py"

SUITE = """\
*** Settings ***
Suite Setup    Log    preparing

*** Test Cases ***
Passing Test
    Log    all good

Failing Test
    Should Be Equal    expected    actual    msg=values differ
"""

PASSING_SUITE = SUITE.replace("expected    actual", "same    same")


def run_robot(workdir: Path, suite: str) -> int:
    tests = workdir / "tests"
    tests.mkdir()
    (tests / "sample.robot").write_text(suite)
    return robot.run(
        str(tests),
        outputdir=str(workdir / "output"),
        output="output.xml",
        log="NONE",
        report="NONE",
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )


def analyze(workdir: Path) -> str:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=workdir, check=True)
    return (workdir / "output" / "result.txt").read_text()


def test_passing_run_is_reported_as_passed(tmp_path):
    assert run_robot(tmp_path, PASSING_SUITE) == 0

    result = analyze(tmp_path)

    assert result.startswith("Main Test Suite: Tests\t|\tPassed: 2\t|\tFailed: 0\n")
    assert "Suite: Sample\t|\tPassed: 2\t|\tFailed: 0" in result
    assert result.endswith("RESULT: TESTS PASSED\n")


def test_failing_run_lists_failed_keyword_and_message(tmp_path):
    assert run_robot(tmp_path, SUITE) == 1

    result = analyze(tmp_path)

    assert result.startswith("Main Test Suite: Tests\t|\tPassed: 1\t|\tFailed: 1\n")
    assert "\tPassing Test\t|\tStatus: 'PASS'" in result
    assert "\tFailing Test\t|\tStatus: 'FAIL'" in result
    assert "Should Be Equal\t|\tStatus: 'FAIL'" in result
    assert "values differ: expected != actual\t|\tLevel: 'FAIL'" in result
    assert result.endswith("RESULT: TESTS FAILED\n")


def test_suite_setup_keywords_are_listed(tmp_path):
    run_robot(tmp_path, SUITE)

    result = analyze(tmp_path)

    assert "Keywords:\n\tLog\t|\tStatus: 'PASS'" in result


def test_missing_output_file_writes_no_result(tmp_path):
    (tmp_path / "output").mkdir()

    subprocess.run([sys.executable, str(SCRIPT)], cwd=tmp_path, check=True, capture_output=True)

    assert not (tmp_path / "output" / "result.txt").exists()

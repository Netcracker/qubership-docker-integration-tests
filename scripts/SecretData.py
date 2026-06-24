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

import os
from pathlib import Path

_DEFAULT_SECRETS_DIR = "/mnt/secrets/env"


def get_variables(secret_dir=None):
    """
    Dynamic Robot Framework variable file.

    Secret files under secret_dir override os.environ keys with the same name.
    Directory: INTEGRATION_TESTS_SECRETS_DIR, or the optional Robot Variables
    argument, defaulting to /mnt/secrets/env.
    """
    if secret_dir is None:
        secret_dir = os.getenv(
            "INTEGRATION_TESTS_SECRETS_DIR", _DEFAULT_SECRETS_DIR
        )

    variables = dict(os.environ)

    secret_path = Path(secret_dir)

    if not secret_path.exists():
        return variables

    for file_path in secret_path.iterdir():
        if not file_path.is_file():
            continue

        variables[file_path.name] = file_path.read_text(
            encoding="utf-8"
        ).rstrip("\r\n")

    return variables

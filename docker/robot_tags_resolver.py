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

import importlib.util
import os


def create_exclude_tags_robot_command(tags: list) -> str:
    return f'-e {"OR".join(tags)}' if tags else ""


def create_exclude_tags_description(tags: dict) -> str:
    if not tags:
        return ""
    title = "The following tags will be excluded with provided reason\n"
    description_list = []
    for tag in tags.items():
        description_list.append(f'{tag[0]}: {tag[1]}')
    tags_with_description = "\n".join(description_list)
    return f'{title}{tags_with_description}'


def resolve_robot_tags(start_directory="./tests", tags_resolver_module="tags_exclusion.py"):
    tags = []
    tags_with_description = {}
    environ = os.environ
    for root, dirs, files in os.walk(start_directory):
        for file in files:
            if file == tags_resolver_module:
                spec = importlib.util.spec_from_file_location(file[:-3], location=os.path.join(root, file))
                foo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(foo)
                new_tags = foo.get_excluded_tags(environ)
                if isinstance(new_tags, dict):
                    tags += list(new_tags.keys())
                    tags_with_description.update(new_tags)
                if isinstance(new_tags, list):
                    tags += new_tags
    tags = set(tags)
    excluded_tags_line = create_exclude_tags_robot_command(tags)
    excluded_tags_description = create_exclude_tags_description(tags_with_description)
    print(f'{excluded_tags_line};{excluded_tags_description};')


resolve_robot_tags()

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

class FileSystem:

    def exists(self, path):
        return os.path.exists(path)

    def makedirs(self, path):
        if not self.exists(path):
            return os.makedirs(path)

    def listdir(self, path):
        return os.listdir(path)

    def remove(self, path):
        if self.exists(path):
            os.remove(path)

    def rmdir(self, path):
        if self.exists(path):
            os.rmdir(path)

    def rmtree(self, path):
        if self.exists(path):
            fsutil.rmtree(path)

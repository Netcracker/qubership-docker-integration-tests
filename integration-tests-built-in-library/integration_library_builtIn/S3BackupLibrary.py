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

from s3_storage import S3Client, S3FileSystem


class S3BackupLibrary(object):

    def __init__(self, url: str, bucket: str, key_id: str, key_secret: str, ssl_verify=False):
        self.s3Client = S3Client(url, bucket, key_id, key_secret, ssl_verify)
        self.S3FileSystem = S3FileSystem(client=self.s3Client)

    def check_bucket_exists(self, bucket_name):
        buckets = self.s3Client.get_list_buckets()
        for bucket in buckets:
            if bucket_name == bucket['Name']:
                return True
        return False

    def get_bucket(self, bucket_name):
        bucket = self.s3Client.resource.Bucket(bucket_name)
        return bucket

    def check_backup_exists(self, path, backup_id):
        backup_file = self.s3Client.list_files(path=f"{path}/{backup_id}")
        return bool(backup_file)

    def remove_backup(self, path):
        self.S3FileSystem.rmtree(path)

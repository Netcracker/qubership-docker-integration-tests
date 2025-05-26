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

import json
import logging
import os
import time

import boto3
from botocore import config
from botocore.exceptions import ClientError
from FileSystemS3 import FileSystem


class S3Client:
    __log = logging.getLogger("S3Client")

    def __init__(self, url, bucket_name, access_key_id: str=None,
                 access_key_secret: str=None, ssl_verify=False):
        """
        S3Client with access to client itself and resource object
        """
        self.url = url
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.bucket_name = bucket_name

        client_config = config.Config(
            region_name="auto",
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret,
            config=client_config,
            verify=ssl_verify,
        )

        self.resource = boto3.resource(
            "s3",
            region_name="auto",
            endpoint_url=self.url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.access_key_secret,
        )

    def create_presigned_url(self, object_name, expiration=3600):
        """Generate a presigned URL to share an S3 object

        :param object_name: string
        :param expiration: Time in seconds for the presigned URL to remain valid
        :return: Presigned URL as string. If error, returns None.
        """

        if expiration is None:
            expiration = 3600
        try:
            response = self.client.generate_presigned_url('get_object',
                                                          Params={'Bucket': self.bucket_name,
                                                                  'Key': object_name},
                                                          ExpiresIn=expiration)
        except ClientError as e:
            self.__log.error(e)
            return None

        return response

    def get_list_buckets(self):
        """ Get list of all buckets
        :return array with objects
        """
        response = self.client.list_buckets()
        return response['Buckets']

    def list_files(self, path):
        """ Get list of files inside folder
        :param path: string
        :return array with object keys
        """
        path = path.strip("/")
        objects = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=path).get(
            'Contents', [])
        files = []
        for obj in objects:
            files.append(obj['Key'])
        return files

    def upload_folder(self, path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                self.upload_file(os.path.join(root, name), os.path.join(root, name))

    def upload_file(self, source, destination: str=None):
        if destination is None:
            destination = source
        destination = destination.strip("/")
        self.client.upload_file(source, self.bucket_name, destination)
        self.__log.info(f"Uploading file {source} to S3 {destination}")

    def download_file(self, src, dest):
        src = src.strip("/")
        self.client.download_file(self.bucket_name, src, dest)
        self.__log.info(f"Downloading file {src} uploaded from S3 to {dest}")

    def download_folder(self, s3_folder, local_dir=None):
        """ Download the contents of a folder directory
        Args:
            s3_folder: the folder path in the s3 bucket
            local_dir: a relative or absolute directory path in the local file system
        """
        self.__log.info(f"Start saving {s3_folder}")
        s3_folder = s3_folder.strip("/")
        bucket = self.resource.Bucket(self.bucket_name)
        for obj in bucket.objects.filter(Prefix=s3_folder):
            target = os.path.join("/", obj.key) if local_dir is None \
                else os.path.join(local_dir, os.path.relpath(obj.key, s3_folder))
            FileSystem.makedirs(os.path.dirname(target))
            if obj.key[-1] == '/':
                continue
            bucket.download_file(obj.key, target)

        self.__log.info(f"Finished saving {s3_folder}")


class S3FileSystem(FileSystem):
    __log = logging.getLogger("S3FileSystem")

    def __init__(self, client: S3Client):
        self.s3client = client

    def listdir(self, path):
        """ Get list of directories
        :param path: string
        :return List of directories inside folder
        """
        dirs = []
        path = path.strip("/") + "/"
        res = self.s3client.client.list_objects_v2(Bucket=self.s3client.bucket_name, Prefix=path, Delimiter="/")
        for prefix in res.get('CommonPrefixes', []):
            split_prefix = prefix["Prefix"].strip("/").split("/")
            if VAULT_DIRNAME_MATCHER.match(split_prefix[-1]):
                dirs.append(split_prefix[-1])
        return dirs

    def exists(self, path, type="dir"):
        """ Check that object exist inside of directory
        :param path: string
        :param type: string. Possible values: "dir" or "file"
        :return List of directories inside folder
        """
        path = path.strip("/")
        if type == "dir":
            resp = self.s3client.client. \
                list_objects(Bucket=self.s3client.bucket_name, Prefix=path, MaxKeys=1)
            return 'Contents' in resp
        elif type == "file":
            try:
                self.s3client.resource.Object(self.s3client.bucket_name, path).load()
            except ClientError as e:
                if e.response['Error']['Code'] == "404":
                    return False
            return True

    def makedirs(self, path):
        super().makedirs(path)

    def read_file(self, path, log):
        path = path.strip("/")
        try:
            response = self.s3client.client.get_object(Bucket=self.s3client.bucket_name, Key=path)
            return json.loads(response['Body'].read())
        except ClientError as e:
            self.__log.warning(f'Could not read file from path {path}, error message: {e}')
            return {}

    def remove(self, path):
        """ Delete all objects inside folder
        :param path: string
        """
        super().remove(path)
        path = path.strip("/")
        failed = False
        bucket = self.s3client.resource.Bucket(self.s3client.bucket_name)
        # does not work in google
        # bucket.objects.filter(Prefix=path).delete()
        objs = bucket.objects.filter(Prefix=path).all()

        try:
            for obj in objs:
                obj.delete()
        except ClientError as e:
            failed = True
            self.__log.warning(f"Could not delete files from path {path}, error message: {e}")

        # to delete all versions if s3 cluster replication is enabled
        try:
            bucket.object_versions.filter(Prefix=path).delete()
            self.__log.debug(f"Permanently deleted all versions of object {path}.")
        except ClientError as e:
            failed = True
            self.__log.info(f"Couldn't delete all versions of {path}. {e}")

        if not failed:
            # ensure delete
            for x in range(5):
                if not self.exists(path):
                    self.__log.debug(f"path {path} has been deleted successfully")
                    return
                self.__log.debug(f"waiting for {path} deletion")
                time.sleep(1)

    def rmdir(self, path):
        """ Delete directories inside folder
        :param path: string
        """
        super().rmdir(path)
        self.remove(path)

    def rmtree(self, path):
        """ It will completely remove the files and subdirectories in a directory
        :param path: string
        """
        super().rmtree(path)
        self.remove(path)

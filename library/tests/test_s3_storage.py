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

"""Tests for s3_storage and S3BackupLibrary against an in-memory S3 server (moto).

The clients use a custom endpoint, as downstream suites do with MinIO, so boto3 and botocore updates
are checked against the same request path.
"""

import json

import boto3
import pytest
from moto import mock_aws
from s3_storage import S3Client, S3FileSystem
from S3BackupLibrary import S3BackupLibrary

ENDPOINT = "http://s3.test:9000"
BUCKET = "backups-bucket"
CREDENTIALS = {"aws_access_key_id": "test-key", "aws_secret_access_key": "test-secret"}


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setenv("MOTO_S3_CUSTOM_ENDPOINTS", ENDPOINT)
    with mock_aws():
        admin = boto3.client("s3", region_name="us-east-1", endpoint_url=ENDPOINT, **CREDENTIALS)
        admin.create_bucket(Bucket=BUCKET)
        yield admin


@pytest.fixture
def client(s3):
    return S3Client(ENDPOINT, BUCKET, CREDENTIALS["aws_access_key_id"], CREDENTIALS["aws_secret_access_key"])


@pytest.fixture
def file_system(client):
    return S3FileSystem(client)


def put(s3, key, body="{}"):
    s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode())


class TestS3Client:
    def test_lists_buckets(self, client):
        assert [bucket["Name"] for bucket in client.get_list_buckets()] == [BUCKET]

    def test_upload_strips_leading_slash_and_lists_files(self, client, tmp_path):
        source = tmp_path / "meta.json"
        source.write_text("{}")

        client.upload_file(str(source), "/backups/20240101T120000/meta.json")

        assert client.list_files("/backups/") == ["backups/20240101T120000/meta.json"]

    def test_download_file(self, client, s3, tmp_path):
        put(s3, "backups/meta.json", '{"id": 1}')

        client.download_file("/backups/meta.json", str(tmp_path / "meta.json"))

        assert json.loads((tmp_path / "meta.json").read_text()) == {"id": 1}

    def test_download_folder_recreates_layout(self, client, s3, tmp_path):
        put(s3, "backups/20240101T120000/meta.json")
        put(s3, "backups/20240101T120000/data/part-0")

        client.download_folder("/backups/", str(tmp_path))

        assert (tmp_path / "20240101T120000" / "meta.json").is_file()
        assert (tmp_path / "20240101T120000" / "data" / "part-0").is_file()

    def test_presigned_url_points_to_endpoint(self, client):
        url = client.create_presigned_url("backups/meta.json", expiration=None)

        assert url.startswith(f"{ENDPOINT}/{BUCKET}/backups/meta.json?")
        assert "Expires=3600" in url or "X-Amz-Expires=3600" in url


class TestS3FileSystem:
    def test_exists_for_directory_and_file(self, file_system, s3):
        put(s3, "backups/20240101T120000/meta.json")

        assert file_system.exists("/backups/")
        assert not file_system.exists("restores")
        assert file_system.exists("backups/20240101T120000/meta.json", type="file")
        assert not file_system.exists("backups/missing.json", type="file")

    def test_listdir_returns_only_backup_folders(self, file_system, s3):
        put(s3, "backups/20240101T120000/meta.json")
        put(s3, "backups/20240102T1200/meta.json")
        put(s3, "backups/granular/meta.json")

        assert sorted(file_system.listdir("backups")) == ["20240101T120000", "20240102T1200"]

    def test_read_file_parses_json(self, file_system, s3):
        put(s3, "backups/meta.json", '{"status": "Successful"}')

        assert file_system.read_file("/backups/meta.json", None) == {"status": "Successful"}

    def test_read_missing_file_returns_empty_dict(self, file_system):
        assert file_system.read_file("backups/missing.json", None) == {}

    def test_remove_deletes_all_objects_under_prefix(self, file_system, client, s3):
        put(s3, "backups/20240101T120000/meta.json")
        put(s3, "backups/20240101T120000/data/part-0")
        put(s3, "backups/20240102T120000/meta.json")

        file_system.remove("backups/20240101T120000")

        assert client.list_files("backups") == ["backups/20240102T120000/meta.json"]

    def test_remove_also_deletes_local_copy(self, file_system, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "meta.json").write_text("{}")

        file_system.remove("meta.json")

        assert not (tmp_path / "meta.json").exists()


class TestS3BackupLibrary:
    @pytest.fixture
    def library(self, s3):
        return S3BackupLibrary(ENDPOINT, BUCKET, CREDENTIALS["aws_access_key_id"], CREDENTIALS["aws_secret_access_key"])

    def test_check_bucket_exists(self, library):
        assert library.check_bucket_exists(BUCKET)
        assert not library.check_bucket_exists("other-bucket")

    def test_get_bucket(self, library):
        assert library.get_bucket(BUCKET).name == BUCKET

    def test_check_backup_exists(self, library, s3):
        put(s3, "backups/20240101T120000/meta.json")

        assert library.check_backup_exists("backups", "20240101T120000")
        assert not library.check_backup_exists("backups", "20240102T120000")

    def test_remove_backup(self, library, s3):
        put(s3, "backups/20240101T120000/meta.json")

        library.remove_backup("backups/20240101T120000")

        assert not library.check_backup_exists("backups", "20240101T120000")

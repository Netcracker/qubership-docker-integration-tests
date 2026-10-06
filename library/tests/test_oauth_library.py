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

"""Tests for OAuthLibrary against a stubbed Identity Provider.

They cover the requests, oauthlib, requests-oauthlib, and PyJWT calls that the library makes.
"""

import json
import re
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
import responses
from OAuthLibrary import OAuthLibrary

IDP = "http://idp.test"


@pytest.fixture
def idp():
    with responses.RequestsMock() as mock:
        yield mock


@pytest.fixture
def library():
    return OAuthLibrary(IDP, "registration-token", "user", "password")


def authorize_with_token(token):
    """Answer the implicit grant like an Identity Provider: redirect with the token in the URL fragment."""

    def callback(request):
        state = parse_qs(urlparse(request.url).query)["state"][0]
        return 302, {"Location": f"{IDP}/callback#access_token={token}&token_type=bearer&state={state}"}, ""

    return callback


def stub_token_flow(idp, token):
    idp.post(f"{IDP}/login", status=200)
    idp.add_callback(
        responses.POST, re.compile(rf"{re.escape(IDP)}/authorize\?.*"), callback=authorize_with_token(token)
    )
    idp.get(f"{IDP}/callback", status=200)


class TestRegisterClient:
    def test_registers_client_and_returns_credentials(self, idp, library):
        idp.post(f"{IDP}/register", json={"client_id": "client-1", "client_secret": "secret-1"})

        assert library.register_client("tests-client") == {"client_id": "client-1", "client_secret": "secret-1"}

        request = idp.calls[0].request
        assert request.headers["Authorization"] == "Bearer registration-token"
        assert json.loads(request.body) == {
            "client_name": "tests-client",
            "redirect_uris": [IDP],
            "application_type": "web",
            "grant_types": "implicit",
            "scope": "profile openid",
        }
        assert library.scope == "profile openid"

    def test_omits_scope_for_grant_types_without_scope(self, idp):
        library = OAuthLibrary(
            IDP, "registration-token", "user", "password", registration_endpoint="/clients", grant_type="password"
        )
        idp.post(f"{IDP}/clients", json={"client_id": "client-1", "client_secret": "secret-1"})

        library.register_client("tests-client", scope="custom")

        assert "scope" not in json.loads(idp.calls[0].request.body)
        assert library.scope == ""


class TestGetToken:
    def test_logs_in_and_returns_token_from_redirect(self, idp, library):
        stub_token_flow(idp, "token-1")

        assert library.get_token("client-1") == "token-1"

        login, authorize = idp.calls[0].request, idp.calls[1].request
        assert parse_qs(login.body) == {"login": ["user"], "password": ["password"]}
        query = parse_qs(urlparse(authorize.url).query)
        assert query["response_type"] == ["token"]
        assert query["client_id"] == ["client-1"]

    def test_raises_when_login_fails(self, idp, library):
        idp.post(f"{IDP}/login", status=401)

        with pytest.raises(Exception, match="401"):
            library.get_token("client-1")


def test_delete_client_deletes_matching_client(idp, library):
    stub_token_flow(idp, "token-1")
    idp.get(f"{IDP}/api/clients", json=[{"clientId": "other", "id": "1"}, {"clientId": "client-1", "id": "2"}])
    idp.delete(f"{IDP}/api/clients/2", json={})

    library.delete_client("client-1")

    list_request = idp.calls[3].request
    assert list_request.headers["Authorization"] == "Bearer token-1"
    assert idp.calls[4].request.method == "DELETE"


def test_get_tenant_reads_claim_without_verifying_signature(library):
    token = jwt.encode({"tenant-id": "tenant-1"}, "a-signing-key-the-library-does-not-know", algorithm="HS256")

    assert library.get_tenant(token) == "tenant-1"

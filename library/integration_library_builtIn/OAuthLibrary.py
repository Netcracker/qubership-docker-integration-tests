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
import os
from contextlib import suppress

import jwt
import requests
from oauthlib.oauth2 import MobileApplicationClient
from requests_oauthlib import OAuth2Session
from robot.api import logger

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

requests.packages.urllib3.disable_warnings()


class OAuthLibrary(object):
    """
    This Robot Framework library provides API to communicate with Identity Provider. It allows you to register own
    client with desired name, receive a token for the client, and remove the client if you no longer need it.

    This is an example of import library with Identity Provider parameters.

    | Library | OAuthLibrary | url=http://identity-management.security-services-ci.svc:8080 | registration_token=1BK2ztNwKMlO0fHKocPQW2glUC0Tg4aN | username=username | password=password |
    """

    def __init__(self, url, registration_token, username, password, registration_endpoint="/register",
                 grant_type="implicit"):
        self.session = requests.session()
        self.url = url
        self.registration_token = registration_token
        self.username = username
        self.password = password
        self.registration_endpoint = registration_endpoint
        self.grant_type = grant_type
        self.scope = ''

    def __del__(self):
        self.session.close()

    def register_client(self, client_name: str, scope='profile openid'):
        """
        Registers client with specified name in Identity Provider.
        :param client_name: the name of new client
        :scope: the scope of new client

        Example:
        | Register Client | elasticsearch-integration-tests-client |
        """
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % str(self.registration_token)
        }

        data = {
            "client_name": str(client_name),
            "redirect_uris": [self.url],
            "application_type": "web",
            "grant_types": self.grant_type
        }

        if 'authorization_code' in self.grant_type or 'implicit' in self.grant_type \
                or 'client_credentials' in self.grant_type:
            data['scope'] = scope
            self.scope = scope

        response = requests.post(f'{self.url}{self.registration_endpoint}', headers=headers, json=data)
        with suppress(Exception):
            logger.info(f'response json: {json.dumps(response.json())}', html=True)

        return {
            "client_id": response.json()['client_id'],
            "client_secret": response.json()['client_secret']
        }

    def delete_client(self, client_id):
        """
        Deletes client from Identity Provider by specified client identifier.
        :param client_id: the identifier of client

        Example:
        | Delete Client | esd5-b3o3-dasdgdf-174 |
        """
        token = self.get_token(client_id)

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % str(token)
        }

        response = requests.get(f'{self.url}/api/clients', headers=headers)

        clients = response.json()

        for client in clients:
            if client["clientId"] == client_id:
                response = requests.delete(f'{self.url}/api/clients/{client["id"]}', headers=headers)
                with suppress(Exception):
                    logger.info(f'response json: {json.dumps(response.json())}', html=True)
                break

    def get_token(self, client_id):
        """
        Obtains JWT access token for specified client.
        :param client_id: the identifier of client

        Example:
        | Get Token | esd5-b3o3-dasdgdf-174 |
        """
        client = MobileApplicationClient(client_id)
        fitbit = OAuth2Session(client_id, client=client, scope=self.scope)
        authorization_url, state = fitbit.authorization_url(f'{self.url}/authorize')
        self.__login()
        response = self.session.post(authorization_url)
        response.raise_for_status()
        token = fitbit.token_from_fragment(response.url).get('access_token')
        return token

    def get_tenant(self, token):
        """
        Receives tenant name from JWT access token.
        :param token: JWT access token

        Example:
        | Get Tenant | eb53o3dasdgdf174... |
        """
        tenant = jwt.decode(token, verify=False)['tenant-id']
        return tenant

    def __login(self):
        login_url = f'{self.url}/login'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'login': self.username, 'password': self.password}
        response = self.session.post(login_url, data=data, headers=headers)
        response.raise_for_status()

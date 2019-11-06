import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

import attr
import pytz
import requests
import singer

from .version import __version__

LOGGER = singer.get_logger()


@attr.s
class WonoloStream(object):

    api_key: str = attr.ib()
    secret_key: str = attr.ib()
    base_url: str = attr.ib(init=False)
    environment: str = attr.ib(validator=attr.validators.in_(["test", "production"]))
    config: Dict = attr.ib(repr=False)
    config_path: str = attr.ib()
    auth_token: str = attr.ib(repr=False, default=None)
    auth_token_expires_at: str = attr.ib(default=None)
    api_version: str = attr.ib(default="v2")

    def __attrs_post_init__(self):
        if self.environment == "test":
            self.base_url = f"https://test.wonolo.com/api_{self.api_version}"
        elif self.environment == "production":
            self.base_url = f"https://api.wonolo.com/api_{self.api_version}"

    @classmethod
    def from_args(cls, args):
        return cls(api_key=args.config.get("api_key"),
                   secret_key=args.config.get("secret_key"),
                   auth_token=args.config.get("auth_token"),
                   auth_token_expires_at=args.config.get("auth_token_expires_at"),
                   api_version=args.config.get("api_version"),
                   environment=args.config.get("environment"),
                   config=args.config,
                   config_path=args.config_path)

    def _construct_headers(self) -> Dict:
        '''Constructs a standard set of headers for HTTPS requests.'''
        headers = requests.utils.default_headers()
        headers["User-Agent"] = f"python-wonolo-tap/{__version__}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Cache-Control"] = "no-cache"
        headers["Content-Length"] = "0"
        headers["Date"] = singer.utils.strftime(singer.utils.now(), '%a, %d %b %Y %H:%M:%S %Z')
        return headers

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        '''Constructs a standard way of making
        a GET request to the Wonolo REST API.
        '''
        url = self.base_url + endpoint
        headers = self._construct_headers()
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        '''Constructs a standard way of making
        a POST request to the Wonolo REST API.
        '''
        url = self.base_url + endpoint
        headers = self._construct_headers()
        response = requests.post(url, headers=headers, params=params, data=data)
        response.raise_for_status()
        return response.json()

    def _generate_auth_token(self) -> Dict:
        '''Uses the API Key and Secret Key provided in the config file
        to generate an Authorization Token using the /authenticate
        API endpoint.
        '''
        data = {
            "api_key": self.api_key,
            "secret_key": self.secret_key
        }
        return self._post(endpoint='/authenticate', data=data)

    def _save_auth_token(self, auth_response: Dict):
        '''Uses the response provided from the /authenticate endpoint
        to save a new auth token and auth token expiration date
        to the exitsing config file.
        '''
        self.config["auth_token"] = auth_response.get("token")
        self.config["auth_token_expires_at"] = auth_response.get("expires_at")
        LOGGER.info('Generating new config..')
        with open(self.args.config_path, 'r+') as f:
            json.dump(self.config, f, indent=2)

    def _check_auth_token(self):
        '''Checks the provided config for a valid auth token.
        '''
        auth_expired = datetime.strptime(self.auth_token_expires_at, '%Y-%m-%dT%H:%M:%SZ') <= singer.utils.now()
        if self.auth_token is None or auth_expired:
            LOGGER.info("Generating new auth token..")
            response = self._generate_auth_token()
            self._save_auth_token(response)
        else:
            LOGGER.info("Using existing auth token..")

    def _list_entity_records(self, endpoint: str) -> List:
        params = {
            "token": self.auth_token
        }
        return self._get(endpoint=endpoint, params=params)

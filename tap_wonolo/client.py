import os
from datetime import datetime, timedelta
from typing import Dict

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
    auth_token: str = attr.ib(repr=False, default=None)
    auth_token_expires_at: str = attr.ib(default=None)
    api_version: str = attr.ib(default="v2")
    base_url: str = attr.ib(init=False)
    environment: str = attr.ib(validator=attr.validators._in(["test", "production"]))

    def __attrs_post_init__(self):
        if self.environment == "test":
            self.base_url = f"https://test.wonolo.com/api_{self.api_version}"
        elif self.environment == "production":
            self.base_url = f"https://api.wonolo.com/api_{self.api_version}"

    @classmethod
    def from_config(cls, config):
        return cls(api_key=config.get("api_key"),
                   secret_key=config.get("secret_key"),
                   auth_token=config.get("auth_token"),
                   auth_token_expires_at=config.get("auth_token_expires_at"),
                   api_version=config.get("api_version"),
                   environment=config.get("environment"))

    def _construct_headers(self) -> Dict:
        '''Constructs a standard set of headers for HTTPS requests.'''
        headers = requests.utils.default_headers()
        headers["Accept"] = "application/json"
        headers["User-Agent"] = f"python-wonolo-tap/{__version__}"
        headers["Content-Type"] = "application/json"
        headers["Date"] = singer.utils.strftime(singer.utils.now(), '%a, %d %b %Y %H:%M:%S %Z')
        return headers

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        '''Constructs a standard way of making
        a GET request to the Wonolo REST API.
        '''
        url = self.BASE_URL + endpoint
        headers = self._construct_headers()
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        '''Constructs a standard way of making
        a POST request to the Wonolo REST API.
        '''
        url = self.BASE_URL + endpoint
        headers = self._construct_headers()
        response = requests.post(url, headers=headers, params=params, data=data)
        response.raise_for_status()
        return response.json()

    def _generate_auth_token(self, api_key: str, secret_key: str) -> Dict:
        '''Uses the API Key and Secret Key provided in the config file
        to generate an Authorization Token using the /authenticate
        API endpoint.
        '''
        data = {
            "api_key": api_key,
            "secret_key": secret_key
        }
        return self._post(endpoint='/authenticate', data=data)

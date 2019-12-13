import json
import os
from datetime import datetime
from typing import Dict, Generator, List, Optional, Set

import attr
import backoff
import requests
import singer

from .version import __version__

LOGGER = singer.get_logger()


def is_fatal_code(e: requests.exceptions.RequestException) -> bool:
    '''Helper function to determine if a Requests reponse status code
    is a "fatal" status code. If it is, the backoff decorator will giveup
    instead of attemtping to backoff.'''
    return 400 <= e.response.status_code < 500 and e.response.status_code != 429


@attr.s
class WonoloStream(object):
    tap_stream_id: Optional[str] = None

    api_key: str = attr.ib()
    secret_key: str = attr.ib()
    environment: str = attr.ib(validator=attr.validators.in_(["test", "production"]))
    config: Dict = attr.ib(repr=False)
    config_path: str = attr.ib()
    state: Dict = attr.ib()
    base_url: str = attr.ib(init=False)
    schema: Dict = attr.ib(init=False)
    auth_token: Optional[str] = attr.ib(repr=False, default=None)
    auth_token_expires_at: Optional[str] = attr.ib(default=None)
    api_version: str = attr.ib(default="v2", validator=attr.validators.instance_of(str))
    params: Dict = attr.ib(init=False, default=None)

    def __attrs_post_init__(self):
        if self.environment == "test":
            self.base_url = f"https://test.wonolo.com/api_{self.api_version}"
        elif self.environment == "production":
            self.base_url = f"https://api.wonolo.com/api_{self.api_version}"

        if self.tap_stream_id is not None:
            self.schema = self._load_schema()

        if self.config.get("streams") is None:
            self.params = {}
        else:
            self.params = self.config.get("streams", {}).get(self.tap_stream_id, {})
            if not isinstance(self.params, dict):
                raise TypeError("Stream parameters must be supplied as JSON.")
            else:
                for key in self.params.keys():
                    if key not in self.valid_params:
                        raise ValueError(f"{key} is not a valid parameter for stream {self.tap_stream_id}")

    @classmethod
    def from_args(cls, args):
        return cls(api_key=args.config.get("api_key"),
                   secret_key=args.config.get("secret_key"),
                   auth_token=args.config.get("auth_token"),
                   auth_token_expires_at=args.config.get("auth_token_expires_at"),
                   api_version=args.config.get("api_version"),
                   environment=args.config.get("environment"),
                   config=args.config,
                   config_path=args.config_path,
                   state=args.state)

    def _get_abs_path(self, path: str) -> str:
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

    def _load_schema(self) -> Dict:
        '''Loads a JSON schema file for a given
        Dayforce resource into a dict representation.
        '''
        schema_path = self._get_abs_path("schemas")
        return singer.utils.load_json(f"{schema_path}/{self.tap_stream_id}.json")

    def _construct_headers(self) -> Dict:
        '''Constructs a standard set of headers for HTTPS requests.'''
        headers = requests.utils.default_headers()
        headers["User-Agent"] = f"python-wonolo-tap/{__version__}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Cache-Control"] = "no-cache"
        headers["Content-Length"] = "0"
        headers["Date"] = singer.utils.strftime(singer.utils.now(), '%a, %d %b %Y %H:%M:%S %Z')
        return headers

    @backoff.on_exception(backoff.fibo,
                          requests.exceptions.HTTPError,
                          max_time=120,
                          giveup=is_fatal_code,
                          logger=LOGGER)
    @backoff.on_exception(backoff.fibo,
                          (requests.exceptions.ConnectionError,
                           requests.exceptions.Timeout),
                          max_time=120,
                          logger=LOGGER)
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
        self.auth_token = auth_response.get("token")
        self.auth_token_expires_at = auth_response.get("expires_at")
        self.config["auth_token"] = auth_response.get("token")
        self.config["auth_token_expires_at"] = auth_response.get("expires_at")
        LOGGER.info('Generating new config..')
        with open(self.config_path, 'r+') as f:
            json.dump(self.config, f, indent=2)

    def _check_auth_token(self):
        '''Checks the provided config for a valid auth token.'''
        if self.auth_token is None:
            LOGGER.info("Generating new auth token..")
            response = self._generate_auth_token()
            self._save_auth_token(response)
        elif datetime.strptime(self.auth_token_expires_at, '%Y-%m-%dT%H:%M:%SZ') <= datetime.utcnow():
            LOGGER.info("Generating new auth token..")
            response = self._generate_auth_token()
            self._save_auth_token(response)
        else:
            LOGGER.info("Using existing auth token..")

    def _yield_records(self, entity: str, params: Optional[Dict] = None) -> Generator[Dict, None, None]:
        '''Yeild individual records for a given entity.'''
        self._check_auth_token()
        if params is None:
            params = {}
        params.update({
            "token": self.auth_token,
            "page": 1,
            "per": 50
        })
        records = self._get(endpoint=f"/{entity}", params=params).get(entity)
        for record in records:
            yield record

        # Paginate
        while len(records) == params.get("per"):
            params["page"] += 1
            records = self._get(endpoint=f"/{entity}", params=params).get(entity)
            if len(records) > 0:
                for record in records:
                    yield record

    def sync(self):
        '''Sync data according to Singer spec.'''
        current_bookmark_str = singer.bookmarks.get_bookmark(state=self.state,
                                                             tap_stream_id=self.tap_stream_id,
                                                             key=self.bookmark_properties)

        if current_bookmark_str is not None:
            self.params.update({self.api_bookmark_param: current_bookmark_str})
            current_bookmark_dt = singer.utils.strptime_to_utc(current_bookmark_str)
        else:
            current_bookmark_dt = None

        with singer.metrics.job_timer(job_type=f"sync_{self.tap_stream_id}"):
            with singer.metrics.record_counter(endpoint=self.tap_stream_id) as counter:
                for record in self._yield_records(entity=self.tap_stream_id, params=self.params):
                    record_bookmark_dt = singer.utils.strptime_to_utc(record.get(self.bookmark_properties))
                    if current_bookmark_dt is None or (record_bookmark_dt > current_bookmark_dt):
                        singer.bookmarks.write_bookmark(state=self.state,
                                                        tap_stream_id=self.tap_stream_id,
                                                        key=self.bookmark_properties,
                                                        val=record.get(self.bookmark_properties))
                        current_bookmark_dt = record_bookmark_dt

                    with singer.Transformer() as transformer:
                        transformed_record = transformer.transform(data=record, schema=self.schema)
                        singer.write_record(stream_name=self.tap_stream_id, time_extracted=singer.utils.now(), record=transformed_record)
                        counter.increment()

    def write_schema_message(self):
        '''Writes a Singer schema message.'''
        return singer.write_schema(stream_name=self.tap_stream_id, schema=self.schema, key_properties=self.key_properties)

    def write_state_message(self):
        '''Writes a Singer state message.'''
        return singer.write_state(self.state)


@attr.s
class JobsStream(WonoloStream):
    tap_stream_id: str = 'jobs'
    key_properties: List[str] = ["id"]
    bookmark_properties: str = "updated_at"
    api_bookmark_param: str = "updated_after"
    replication_method: str = 'INCREMENTAL'
    valid_params: Set[str] = {
        "state",
        "job_request_id",
        "classification",
        "w2_hourly_rate",
        "w2_pay_status",
        "updated_before",
        "updated_after"
    }


@attr.s
class JobRequestsStream(WonoloStream):
    tap_stream_id: str = 'job_requests'
    key_properties: List[str] = ["id"]
    bookmark_properties: str = "updated_at"
    api_bookmark_param: str = "updated_after"
    replication_method: str = 'INCREMENTAL'
    valid_params: Set[str] = {
        "state",
        "company_id",
        "multi_day_job_request_id",
        "classification",
        "w2_hourly_rate",
        "updated_before",
        "updated_after",
        "agent_code"
    }


@attr.s
class UsersStream(WonoloStream):
    tap_stream_id: str = 'users'
    key_properties: List[str] = ["id"]
    bookmark_properties: str = "updated_at"
    api_bookmark_param: str = "updated_after"
    replication_method: str = 'INCREMENTAL'
    valid_params: Set[str] = {
        "type",
        "email",
        "first_name",
        "last_name",
        "external_id",
        "onboarding_last_state",
        "w2_onboarding_status",
        "w2_employee_id",
        "address_state",
        "drug_tested",
        "updated_before",
        "updated_after"
    }

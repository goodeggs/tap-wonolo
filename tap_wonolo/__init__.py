import logging
import os

import rollbar
import singer
from rollbar.logger import RollbarHandler

from .client import WonoloStream


ROLLBAR_ACCESS_TOKEN = os.environ["ROLLBAR_ACCESS_TOKEN"]
ROLLBAR_ENVIRONMENT = os.environ["ROLLBAR_ENVIRONMENT"]

LOGGER = singer.get_logger()

rollbar.init(ROLLBAR_ACCESS_TOKEN, ROLLBAR_ENVIRONMENT)
rollbar_handler = RollbarHandler()
rollbar_handler.setLevel(logging.WARNING)
LOGGER.addHandler(rollbar_handler)

REQUIRED_CONFIG_KEYS = [
    "api_key",
    "secret_key",
    "environment"
]

def discover():
    pass

def sync(args):
    wonolo = WonoloStream.from_args(args)
    print(wonolo)
    response = wonolo._generate_auth_token()
    print(response)

def main():
    args = singer.parse_args(required_config_keys=REQUIRED_CONFIG_KEYS)
    if args.discover:
        discover()
    else:
        sync(args)

if __name__ == "__main__":
    main()

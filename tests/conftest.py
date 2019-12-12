import argparse
import json

import pytest

from tap_wonolo.client import WonoloStream

CONFIG_PATH = 'tests/data/test.config.json'
STATE_PATH = 'tests/data/test.state.json'


@pytest.fixture(scope='session')
def config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


@pytest.fixture(scope='session')
def state():
    with open(STATE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope='session')
def args(config, state):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    parser.add_argument('--state')
    args = parser.parse_args()
    args.config = config
    setattr(args, 'config_path', CONFIG_PATH)
    args.state = state
    setattr(args, 'state_path', STATE_PATH)
    return args


@pytest.fixture(scope='session')
def client(config, state):
    return WonoloStream(api_key=config.get("api_key"),
                        secret_key=config.get("secret_key"),
                        api_version=config.get("api_version"),
                        environment=config.get("environment"),
                        config=config,
                        config_path=CONFIG_PATH,
                        state=state)

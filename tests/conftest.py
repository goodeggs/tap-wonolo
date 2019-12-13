import argparse
import json

import pytest

from tap_wonolo.client import JobRequestsStream, JobsStream, UsersStream


@pytest.fixture(scope='function')
def config(shared_datadir):
    with open(shared_datadir / 'test.config.json') as f:
        return json.load(f)


@pytest.fixture(scope='function')
def state(shared_datadir):
    with open(shared_datadir / 'test.state.json') as f:
        return json.load(f)


@pytest.fixture(scope='function')
def args(config, state, shared_datadir):
    args = argparse.Namespace()
    setattr(args, 'config', config)
    setattr(args, 'state', state)
    setattr(args, 'config_path', shared_datadir / 'test.config.json')
    setattr(args, 'state_path', shared_datadir / 'test.state.json')
    return args


@pytest.fixture(scope='function', params={JobsStream, JobRequestsStream, UsersStream})
def client(config, state, shared_datadir, request):
    return request.param(api_key=config.get("api_key"),
                         secret_key=config.get("secret_key"),
                         api_version=config.get("api_version"),
                         environment=config.get("environment"),
                         config=config,
                         config_path=shared_datadir / 'test.config.json',
                         state=state)

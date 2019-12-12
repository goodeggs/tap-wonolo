import pytest
import requests

from tap_wonolo.client import WonoloStream, is_fatal_code


@pytest.mark.parametrize('status_code', [400, 401, 403, 404, 429,
                                         pytest.param(500, marks=pytest.mark.xfail),
                                         pytest.param(502, marks=pytest.mark.xfail),
                                         pytest.param(503, marks=pytest.mark.xfail),
                                         pytest.param(504, marks=pytest.mark.xfail)])
def test_is_fatal_code(status_code):
    resp = requests.models.Response()
    resp.status_code = status_code
    exc = requests.exceptions.RequestException(response=resp)
    assert is_fatal_code(exc)


def test_client_from_args_class_method(args):
    client = WonoloStream.from_args(args)
    assert client.api_key == "foo"
    assert client.secret_key == "bar"
    assert client.api_version == "v2"
    assert client.environment == "test"
    assert client.config_path == "tests/data/test.config.json"

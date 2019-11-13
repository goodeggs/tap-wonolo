# tap-wonolo
[![PyPI version](https://badge.fury.io/py/tap-wonolo.svg)](https://badge.fury.io/py/tap-wonolo)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Versions](https://img.shields.io/badge/python-3.6%20%7C%203.7-blue.svg)](https://pypi.python.org/pypi/ansicolortags/)
[![Build Status](https://travis-ci.com/goodeggs/tap-wonolo.svg?branch=master)](https://travis-ci.com/goodeggs/tap-wonolo.svg?branch=master)

A [Singer](https://www.singer.io/) tap for extracting data from the [Wonolo REST API v2](https://wonolo.readme.io/docs/getting-started).

## Installation

Since package dependencies tend to conflict between various taps and targets, Singer [recommends](https://github.com/singer-io/getting-started/blob/master/docs/RUNNING_AND_DEVELOPING.md#running-singer-with-python) installing taps and targets into their own isolated virtual environments:

### Install Wonolo Tap

```bash
$ python3 -m venv ~/.venvs/tap-wonolo
$ source ~/.venvs/tap-wonolo/bin/activate
$ pip3 install tap-wonolo
$ deactivate
```

### Install Stitch Target (optional)

```bash
$ python3 -m venv ~/.venvs/target-stitch
$ source ~/.venvs/target-stitch/bin/activate
$ pip3 install target-stitch
$ deactivate
```

## Configuration

The tap accepts a JSON-formatted configuration file as arguments. This configuration file has four required fields:

1. `api_key`: A valid Wonolo API key.
2. `secret_key`: A valid Wonolo secret key.
3. `environment`: A valid Wonolo enviroment (either "test" or "production").

An bare-bones Wonolo configuration may file may look like the following:

```json
{
  "api_key": "foo",
  "secret_key": "bar",
  "environment": "test"
}
```

### Authentication
If no `auth_token` key is supplied in the configuration file, the tap will automatically request one via the API and write it back to the config file:

```json
{
  "api_key": "foo",
  "secret_key": "bar",
  "environment": "test",
  "auth_token": "foobar",
  "auth_token_expires_at": "2019-11-08T00:00:20Z",
}
```

The tap will then use the aforementioned `auth_token` to authenticate to the API, until the `auth_token` becomes invalidated, at which point the tap will automatically request and record a new `auth_token` from the API.

### Granular Stream Configuration

Additionally, you may specify more granular configurations for individual streams. Each key under a stream should represent a valid API request parameter for that endpoint. A more fleshed-out configuration file may look similar to the following:

```json
{
  "api_key": "foo",
  "secret_key": "bar",
  "environment": "test",
  "api_version": "v2",
  "streams": {
    "jobs": {
      "state": "fulfilled",
      "company_id": "1234",
      "classification": "w2"
    },
    "job_requests": {
      "w2_hourly_rate": 21.5,
      "updated_after": "2017-05-24T17:01:19.391-07:00"
    }
  }
}
```

## Streams

The current version of the tap syncs three distinct [Streams](https://github.com/singer-io/getting-started/blob/master/docs/SYNC_MODE.md#streams):
1. `Jobs`: [Endpoint Documentation](https://wonolo.readme.io/docs/entities-in-the-api#section-jobs)
2. `Job Requests`: [Endpoint Documentation](https://wonolo.readme.io/docs/entities-in-the-api#section-job-requests)
3. `Users`: [Endpoint Documentation](https://wonolo.readme.io/docs/entities-in-the-api#section-users)

## Discovery

Singer taps describe the data that a stream supports via a [Discovery](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode) process. You can run the Dayforce tap in Discovery mode by passing the `--discover` flag at runtime:

```bash
$ ~/.venvs/tap-wonolo/bin/tap-wonolo --config=config/wonolo.config.json --discover
```

The tap will generate a [Catalog](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#the-catalog) to stdout. To pass the Catalog to a file instead, simply redirect it to a file:s

```bash
$ ~/.venvs/tap-wonolo/bin/tap-wonolo --config=config/wonolo.config.json --discover > catalog.json
```

## Sync to stdout

Running a tap in [Sync mode](https://github.com/singer-io/getting-started/blob/master/docs/SYNC_MODE.md#sync-mode) will extract data from the various selected Streams. In order to run a tap in Sync mode and have messages emitted to stdout, pass a valid configuration file and catalog file:

```bash
$ ~/.venvs/tap-wonolo/bin/tap-wonolo --config=config/wonolo.config.json --catalog=catalog.json
```

The tap will emit occasional [Metric](https://github.com/singer-io/getting-started/blob/master/docs/SYNC_MODE.md#metric-messages), [Schema](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md#schema-message), [Record](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md#record-message), and [State messages](https://github.com/singer-io/getting-started/blob/master/docs/SPEC.md#state-message). You can persist State between runs by redirecting messages to a file:

```bash
$ ~/.venvs/tap-wonolo/bin/tap-wonolo --config=config/wonolo.config.json --catalog=catalog.json >> state.json
$ tail -1 state.json > state.json.tmp
$ mv state.json.tmp state.json
```

## Sync to Stitch

You can also send the output of the tap to [Stitch Data](https://www.stitchdata.com/) for loading into the data warehouse. To do this, first create a JSON-formatted configuration for Stitch. This configuration file has two required fields:
1. `client_id`: The ID associated with the Stitch Data account you'll be sending data to.
2. `token` The token associated with the specific [Import API integration](https://www.stitchdata.com/docs/integrations/import-api/) within the Stitch Data account.

An example configuration file will look as follows:

```json
{
  "client_id": 1234,
  "token": "foobarfoobar"
}
```

Once the configuration file is created, simply pipe the output of the tap to the Stitch Data target and supply the target with the newly created configuration file:

```bash
$ ~/.venvs/tap-wonolo/bin/tap-wonolo --config=config/dayforce.config.json --catalog=catalog.json --state=state.json | ~/.venvs/target-stitch/bin/target-stitch --config=config/stitch.config.json >> state.json
$ tail -1 state.json > state.json.tmp
$ mv state.json.tmp state.json
```

## Contributing

The first step to contributing is getting a copy of the source code. First, [fork `tap-wonolo` on GitHub](https://github.com/goodeggs/tap-wonolo/fork). Then, `cd` into the directory where you want your copy of the source code to live and clone the source code:

```bash
$ git clone git@github.com:YourGitHubName/tap-wonolo.git
```

Now that you have a copy of the source code on your local machine, you can leverage [Pipenv](https://docs.pipenv.org/en/latest/) and the corresponding `Pipfile` to install of the development dependencies within a virtual environment:

```bash
$ pipenv install --three --dev
```

This command will create an isolated virtual environment for your `tap-wonolo` project and install all the development dependencies defined within the `Pipfile` inside of the environment. You can then enter a shell within the environment:

```bash
$ pipenv shell
```

Or, you can run individual commands within the environment without entering the shell:

```bash
$ pipenv run <command>
```

For example, to format your code using [isort](https://github.com/timothycrosley/isort) and [flake8](http://flake8.pycqa.org/en/latest/index.html) before commiting changes, run the following commands:

```bash
$ pipenv run make isort
$ pipenv run make flake8
```

You can also run the entire testing suite before committing using [tox](https://tox.readthedocs.io/en/latest/):

```bash
$ pipenv run tox
```

Finally, you can run your local version of the tap within the virtual environment using a command like the following:

```bash
$ pipenv run tap-wonolo --config=config/dayforce.config.json --catalog=catalog.json
```

Once you've confirmed that your changes work and the testing suite passes, feel free to put out a PR!

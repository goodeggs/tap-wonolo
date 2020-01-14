import json
import os
import sys

import rollbar
import singer

from .client import JobRequestsStream, JobsStream, UsersStream

AVAILABLE_STREAMS = {
    JobsStream,
    JobRequestsStream,
    UsersStream
}

REQUIRED_CONFIG_KEYS = [
    "api_key",
    "secret_key",
    "environment"
]

LOGGER = singer.get_logger()

try:
    ROLLBAR_ACCESS_TOKEN = os.environ["ROLLBAR_ACCESS_TOKEN"]
    ROLLBAR_ENVIRONMENT = os.environ["ROLLBAR_ENVIRONMENT"]
except KeyError:
    LOGGER.info("No Rollbar environment variables found. Rollbar logging disabled..")
    log_to_rollbar = False
else:
    rollbar.init(ROLLBAR_ACCESS_TOKEN, ROLLBAR_ENVIRONMENT)
    log_to_rollbar = True


def discover(args, select_all=False):
    LOGGER.info('Starting discovery..')

    catalog = {"streams": []}
    for available_stream in AVAILABLE_STREAMS:
        stream = available_stream.from_args(args)
        catalog_entry = {
            "stream": stream.tap_stream_id,
            "tap_stream_id": stream.tap_stream_id,
            "schema": stream.schema,
            "metadata": singer.metadata.get_standard_metadata(schema=stream.schema,
                                                              key_properties=stream.key_properties,
                                                              valid_replication_keys=stream.bookmark_properties,
                                                              replication_method=stream.replication_method)
        }

        if select_all is True:
            catalog_entry["metadata"][0]["metadata"]["selected"] = True
        catalog["streams"].append(catalog_entry)

    print(json.dumps(catalog, indent=2))


def sync(args):
    LOGGER.info('Starting sync..')

    if not args.state:
        args.state = {"bookmarks": {}}

    selected_streams = {catalog_entry.stream for catalog_entry in args.catalog.get_selected_streams(args.state)}

    for available_stream in AVAILABLE_STREAMS:
        if available_stream.tap_stream_id in selected_streams:
            stream = available_stream.from_args(args)
            LOGGER.info(f"Starting sync for stream {stream.tap_stream_id}..")
            singer.bookmarks.set_currently_syncing(state=args.state, tap_stream_id=stream.tap_stream_id)
            stream.write_state_message()
            stream.write_schema_message()
            stream.sync()
            singer.bookmarks.set_currently_syncing(state=args.state, tap_stream_id=None)
            stream.write_state_message()


def _main():
    args = singer.parse_args(required_config_keys=REQUIRED_CONFIG_KEYS)
    if args.discover:
        discover(args, select_all=True)
    else:
        sync(args)


def main():
    try:
        _main()
    except Exception:
        if log_to_rollbar is True:
            LOGGER.info("Reporting exception info to Rollbar..")
            rollbar.report_exc_info()
        LOGGER.exception(msg="Uncaught Exception..")
        sys.exit(1)


if __name__ == "__main__":
    main()

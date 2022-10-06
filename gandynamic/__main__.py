import logging
from cerberus import Validator
from gandynamic.constants import CONFIGURATION_SCHEMA
import os
import json
import yaml
import argparse
from gandynamic import Gandynamic, get_public_ipv4


def main():
    # logging configuration
    log_level = os.environ.get("GANDYNAMIC_LOG_LEVEL")
    if not log_level:
        log_level = "INFO"
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # arguments parsing
    parser = argparse.ArgumentParser(description="Update gandi dynamic record")
    parser.add_argument(
        "config_file",
        type=str,
        help="configuration file",
    )
    args = parser.parse_args()

    # configuration loading
    logging.info(f"Loading configuration from {args.config_file}")
    with open(args.config_file) as config_file:
        params = yaml.load(config_file, Loader=yaml.Loader)

    # configuration validation
    v = Validator(CONFIGURATION_SCHEMA, require_all=True, purge_unknown=True)
    if v.validate(params):
        params = v.normalized(params)
        logging.debug("Configuration file is valid.")
        logging.debug(f"Configuration: {params}")
    else:
        logging.error("Configuration file is invalid.")
        raise ValueError(f"Issues found in configuration file: {v.errors}")

    # Gandi API key envvar loading
    if os.environ.get("GANDYNAMIC_GANDI_API_KEY"):
        logging.info(
            "Using Gandi api key from GANDYNAMIC_GANDI_API_KEY environment variable."
        )
        api_key = os.environ["GANDYNAMIC_GANDI_API_KEY"]
    elif params.get("api_key"):
        logging.info(
            "No api key specified in environment variable, using the one specified in config file."
        )
        api_key = params["api_key"]
    else:
        raise ValueError(
            "No Gandi api key found in environment variable nor in config file."
        )

    logging.info(f"Getting public ipv4 from {params['public_ip_service']}...")
    public_ipv4 = get_public_ipv4(params["public_ip_service"])
    logging.info(f"Our public ipv4 is {public_ipv4}")

    app = Gandynamic(public_ipv4, params["cache_file"], api_key, params["records"])

    app.run()


if __name__ == "__main__":
    main()

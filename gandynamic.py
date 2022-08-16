#! /usr/bin/env python3

import string
import requests
import argparse
import logging
import yaml
import json
import socket
import os
import requests.packages.urllib3.util.connection as urllib3_cn
from cerberus import Validator
from deepmerge import always_merger

DEFAULT_TTL = 600
PUBLIC_IP_PROVIDERS = {
    "ifconfig.co": {"url": "https://ifconfig.co/ip"},
    "ifconfig.me": {"url": "https://ifconfig.me/ip"},
    "icanhazip.com": {"url": "http://icanhazip.com"},
    "ipify.org": {"url": "http://api.ipify.org"},
    "ipinfo.io": {"url": "http://ipinfo.io/ip"},
}
CONFIGURATION_SCHEMA = {
    "cache_file": {
        "type": "string",
        "default": "cache.json",
    },
    "public_ip_service": {
        "type": "string",
        "allowed": list(PUBLIC_IP_PROVIDERS.keys()),
        "default": "ifconfig.co",
    },
    "records": {
        "type": "list",
        "minlength": 1,
        "schema": {
            "type": "dict",
            "require_all": True,
            "schema": {
                "domain": {"type": "string"},
                "subdomain": {"type": "string"},
                "ttl": {"type": "integer", "default": DEFAULT_TTL},
            },
        },
    },
}


class RecordsCache:
    def __init__(self, file_path):
        logging.debug(f"Starting records cache using {file_path} for persistence.")
        self.file_path = file_path
        self.__load_cache()

    def __load_cache(self):
        try:
            logging.debug(f"Loading records cache from {self.file_path}...")
            with open(self.file_path, "r") as file:
                self.__content = json.load(file)
                logging.debug(f"Loading records cache from {self.file_path}...done.")
        except FileNotFoundError:
            logging.debug("No cache file found, starting with an empty cache.")
            self.__content = {}
        except OSError as e:
            logging.error(f"Could not open file: {e}")
            raise

    def __save_cache(self):
        try:
            logging.debug(f"Saving cache content to {self.file_path}...")
            with open(self.file_path, "w") as file:
                json.dump(self.__content, file)
                logging.debug(f"Saving cache content to {self.file_path}...done.")
        except OSError as e:
            logging.error(f"Could not open file: {e}")
            raise

    def get(self, domain, subdomain, record_type):
        try:
            logging.debug(
                f"Fetching record {domain}/{subdomain}/{record_type} values from cache..."
            )
            cached_record = self.__content[domain][subdomain][record_type]
            logging.debug(
                f"Fetching record {domain}/{subdomain}/{record_type} values from cache...done."
            )
            return cached_record
        except KeyError:
            logging.debug(f"No {domain}/{subdomain}/{record_type} key found in cache.")
            return None

    def put(self, domain, subdomain, record_type, ttl, value):
        logging.debug(
            f"Putting {{value: {value}, ttl: {ttl}}} to {domain}/{subdomain}/{record_type} record cache entry..."
        )
        record_entry = {
            domain: {subdomain: {record_type: {"value": value, "ttl": ttl}}}
        }
        self.content = always_merger.merge(self.__content, record_entry)
        self.__save_cache()
        logging.debug(
            f"Putting {{value: {value}, ttl: {ttl}}} to {domain}/{subdomain}/{record_type} record cache entry...done."
        )

    def is_cached_record_up_to_date(self, domain, subdomain, record_type, ttl, value):
        logging.debug(
            f"Checking if values {{value: {value}, ttl: {ttl}}} are different than the ones cached for {domain}/{subdomain}/{record_type} record..."
        )
        cached_record_values = self.get(domain, subdomain, record_type)
        if cached_record_values:
            if (
                cached_record_values["value"] == value
                and cached_record_values["ttl"] == ttl
            ):
                logging.debug(
                    f"Values {{value: {value}, ttl: {ttl}}} are already cached for {domain}/{subdomain}/{record_type} record."
                )
                return True
        logging.debug(
            f"Values {{value: {value}, ttl: {ttl}}} are not in cache for {domain}/{subdomain}/{record_type} record."
        )
        return False


def ipv4_family():
    """
    force ipv4 when fetching public IP
    """
    family = socket.AF_INET
    return family


def get_public_ipv4(ip_public_service):
    urllib3_cn.allowed_gai_family = ipv4_family
    r = requests.get(PUBLIC_IP_PROVIDERS[ip_public_service]["url"])
    if r.status_code == 200:
        return r.text.strip()  # we strip because some services output ends with a \n
    else:
        raise RuntimeError(
            f'{ip_public_service} returned an unexpected answer: "code: {r.status_code}, message: {r.text}"'
        )


class Gandynamic:
    def __init__(self, public_ipv4, cache_file_path, api_key, records):
        logging.debug("Instanciating Gandynamic class.")
        self.public_ipv4 = public_ipv4
        self.api_key = api_key
        self.records = records
        self.records_cache = RecordsCache(cache_file_path)
        self.zones_hrefs = {}

    def get_zone_href(self, domain):
        logging.debug(f"Getting `domain_records_href` for domain `{domain}`.")
        headers = {"Authorization": f"Apikey {self.api_key}"}
        r = requests.get(
            f"https://api.gandi.net/v5/livedns/domains/{domain}", headers=headers
        )
        if r.status_code == 200:
            zone_href = r.json()["domain_records_href"]
            logging.debug(
                f"`domain_records_href` for domain `{domain}` is: {zone_href}"
            )
            return zone_href
        elif r.status_code == 401:
            logging.error("Your Gandi API key seems invalid.")
        elif r.status_code == 403:
            logging.error(
                f"It seems that your API key is not authorized to get information for domain {domain}."
            )

        raise RuntimeError(
            f'Gandi API returned an unexpected answer: "code: {r.status_code}, message: {r.text}"'
        )

    def get_cached_zone_href(self, domain):
        logging.debug(f"Getting zone href for domain {domain}...")
        if self.zones_hrefs.get(domain):
            zone_href = self.zones_hrefs[domain]
            logging.debug(
                f"Zone href for domain { domain } has already been fetched and is { zone_href }."
            )
        else:
            logging.debug(f"Fetching zone href for domain { domain }...")
            zone_href = self.get_zone_href(domain)
            logging.debug(
                f"Zone href for domain { domain } is {zone_href}, adding it to cache."
            )
            self.zones_hrefs[domain] = zone_href
        return zone_href

    def put_record(self, domain, subdomain, record_type, ttl, value):
        zone_href = self.get_cached_zone_href(domain)
        headers = {"Authorization": f"Apikey {self.api_key}"}
        data = {
            "rrset_name": subdomain,
            "rrset_type": record_type,
            "rrset_ttl": ttl,
            "rrset_values": [value],
        }
        url = f"{zone_href}/{subdomain}/{record_type}"
        r = requests.put(url, headers=headers, json=data)
        logging.debug(f"Gandi API responded `{r.status_code} {r.text}`.")
        if r.status_code == 201:
            logging.info(
                f'DNS Record "{ subdomain }.{ domain } { ttl} IN A { self.public_ipv4 }" successfully put to Gandi.'
            )
            self.records_cache.put(domain, subdomain, "A", ttl, self.public_ipv4)
        else:
            raise ValueError(
                f"Gandi returned an error at our update request: `{r.status_code} {r.text}`."
            )

    def run(self):
        for record in self.records:
            logging.info(f"Starting run for {record['subdomain']}.{record['domain']}")
            logging.debug(
                f"Checking if {record['subdomain']}.{record['domain']} is already in the wanted state..."
            )
            if self.records_cache.is_cached_record_up_to_date(
                record["domain"],
                record["subdomain"],
                "A",
                record["ttl"],
                self.public_ipv4,
            ):
                logging.info(
                    f"{record['subdomain']}.{record['domain']} is already in the wanted state, nothing to do."
                )
            else:
                logging.info(
                    f"{record['subdomain']}.{record['domain']} is not in the wanted state, needs an update."
                )

                self.put_record(
                    record["domain"],
                    record["subdomain"],
                    "A",
                    record["ttl"],
                    self.public_ipv4,
                )

            logging.info(f"Run for {record['subdomain']}.{record['domain']} finished.")


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

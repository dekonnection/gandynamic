#! /usr/bin/env python3

import requests
import logging
import socket
from requests.packages.urllib3.util import connection as urllib3_cn
from gandynamic.constants import PUBLIC_IP_PROVIDERS
from gandynamic import RecordsCache


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

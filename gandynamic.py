#! /usr/bin/env python3

import requests
import argparse
import logging
import yaml
import socket
import requests.packages.urllib3.util.connection as urllib3_cn


def allowed_gai_family():
    """
    force ipv4 when fetching public IP
    """
    family = socket.AF_INET
    return family


def get_public_ipv4(ip_public_service):
    if ip_public_service == "ifconfig.co":
        urllib3_cn.allowed_gai_family = allowed_gai_family
        r = requests.get("https://ifconfig.co/ip")
        if r.status_code == 200:
            return r.text.strip()
        else:
            raise RuntimeError(
                f'{ip_public_service} returned an unexpected answer: "code: {r.status_code}, message: {r.text}"'
            )
    else:
        raise ValueError("Only `ifconfig.co` is supported for now.")


def get_zone_href(gandi_api_key, domain):
    logging.debug(f"Getting `domain_records_href` for domain `{domain}`.")
    headers = {"Authorization": f"Apikey {gandi_api_key}"}
    r = requests.get(
        f"https://api.gandi.net/v5/livedns/domains/{domain}", headers=headers
    )
    if r.status_code == 200:
        zone_href = r.json()["domain_records_href"]
        logging.debug(f"`domain_records_href` for domain `{domain}` is: {zone_href}")
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


def update_record(gandi_api_key, zone_href, domain, subdomain, record_type, ttl, value):
    headers = {"X-Api-Key": gandi_api_key}
    data = {
        "rrset_name": subdomain,
        "rrset_type": record_type,
        "rrset_ttl": ttl,
        "rrset_values": [value],
    }
    url = f"{zone_href}/{subdomain}/{record_type}"
    r = requests.put(url, headers=headers, json=data)


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Update gandi dynamic record")

    parser.add_argument(
        "config_file",
        type=str,
        help="configuration file",
    )

    args = parser.parse_args()

    logging.info(f"Loading configuration from {args.config_file}")
    with open(args.config_file) as config_file:
        params = yaml.load(config_file, Loader=yaml.Loader)

    logging.info(f"Getting public ipv4 from {params['public_ip_service']}...")
    public_ipv4 = get_public_ipv4(params["public_ip_service"])
    logging.info(f"Our public ipv4 is {public_ipv4}")

    for record in params["records"]:
        zone_href = get_zone_href("dFhYX93Zo6bMa2LBBYlM06Ov", record["domain"])


if __name__ == "__main__":
    main()

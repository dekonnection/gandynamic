#!/bin/bash
# original script from https://virtuallytd.com/post/dynamic-dns-using-gandi/

check_return () {
    if [[ $1 -ne 0 ]]; then
        echo -e "[ERROR] Last command failed with code $1, will exit now." >&2
        exit 1
    fi
}

echo "INFO: starting Gandi dynamic dns updater."

if [[ -z $API_KEY ]] || [[ -z $DOMAIN ]] || [[ -z $SUBDOMAIN ]] || [[ -z $TTL ]]
then
  echo "ERROR: please set \$API_KEY, \$DOMAIN, \$SUBDOMAIN and \$TTL. Will exit."
  exit 1
fi

EXT_IP=$(curl -f -4 -s ifconfig.co)  
check_return $?
echo "INFO: Public IP detected: ${EXT_IP}"

CURRENT_ZONE_HREF=$(curl -f -s -H "X-Api-Key: $API_KEY" https://dns.api.gandi.net/api/v5/domains/$DOMAIN | jq -r '.zone_records_href')
check_return $?
echo "INFO: current zone fetched: ${CURRENT_ZONE_HREF}"

GANDI_UPDATE=$(curl -f -X PUT -H "Content-Type: application/json" \
        -H "X-Api-Key: $API_KEY" \
        -d "{\"rrset_name\": \"$SUBDOMAIN\",
             \"rrset_type\": \"A\",
             \"rrset_ttl\": \"$TTL\",
             \"rrset_values\": [\"$EXT_IP\"]}" \
        "$CURRENT_ZONE_HREF/$SUBDOMAIN/A" 2> /dev/null)
check_return $?
echo "INFO: gandi update status: ${GANDI_UPDATE}"


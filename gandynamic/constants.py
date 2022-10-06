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

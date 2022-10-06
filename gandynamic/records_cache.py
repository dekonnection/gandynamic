import logging
import json
from deepmerge import always_merger


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

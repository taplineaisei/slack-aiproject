import csv
import logging
from typing import Dict, Optional, Literal

# ✅ List of your internal domains
INTERNAL_DOMAINS = ["sey-media.com", "leadacquisition.io"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetadataLoader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MetadataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self, csv_path: str = 'channel_metadata.csv'):
        if not hasattr(self, '_initialized'):
            self.csv_path = csv_path
            self.metadata = self._load_metadata()
            self._initialized = True

    def _load_metadata(self) -> Dict[str, Dict[str, str]]:
        metadata_map = {}
        try:
            with open(self.csv_path, mode='r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    channel_name = row.get('channel_name')
                    if channel_name:
                        metadata_map[channel_name] = {
                            "channel_url": row.get("channel_url")
                        }
                    else:
                        logging.warning("Skipping row due to missing 'channel_name': %s", row)
            logging.info("Loaded metadata for %d channels.", len(metadata_map))
        except FileNotFoundError:
            logging.error("Metadata file not found at path: %s", self.csv_path)
            return {}
        except Exception as e:
            logging.error("Error loading metadata: %s", e, exc_info=True)
            return {}
        return metadata_map

    def get_metadata_by_channel(self, channel_name: str) -> Optional[Dict[str, str]]:
        return self.metadata.get(channel_name)

    def get_role(self, user_email: str) -> Literal["client", "internal", "unknown"]:
        if not user_email or '@' not in user_email:
            return "unknown"

        user_domain = user_email.split('@')[-1].lower()
        if user_domain in INTERNAL_DOMAINS:
            return "internal"
        return "client"

metadata_loader = MetadataLoader()

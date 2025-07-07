import csv
import logging
from typing import Dict, Optional, Literal

# Add a list of domains you and your team use
INTERNAL_DOMAINS = ["sey-media.com", "leadacquisition.io"]  # Add as many as you need


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MetadataLoader:
    """
    Loads and provides access to channel metadata from a CSV file.
    """
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
        """
        Loads the channel metadata from the CSV file into a dictionary.

        Returns:
            A dictionary mapping channel names to their metadata.
        """
        metadata_map = {}
        try:
            with open(self.csv_path, mode='r', encoding='utf-8') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    channel_name = row.get('channel_name')
                    if channel_name:
                        metadata_map[channel_name] = {
                            "client_name": row.get("client_name"),
                            "email_domain": row.get("client_email_domain"),
                            "channel_url": row.get("channel_url")
                        }
                    else:
                        logging.warning("Skipping row in CSV due to missing 'channel_name': %s", row)
            logging.info("Successfully loaded metadata for %d channels.", len(metadata_map))
        except FileNotFoundError:
            logging.error("Metadata file not found at path: %s", self.csv_path)
            # Depending on strictness, we might want to exit or raise an exception
            # For now, we'll return an empty map and log the error.
            return {}
        except Exception as e:
            logging.error("An unexpected error occurred while loading metadata: %s", e, exc_info=True)
            return {}
        return metadata_map

    def get_metadata_by_channel(self, channel_name: str) -> Optional[Dict[str, str]]:
        """
        Retrieves metadata for a specific channel.

        Args:
            channel_name: The name of the channel.

        Returns:
            A dictionary containing the channel's metadata, or None if not found.
        """
        return self.metadata.get(channel_name)

    def get_role(self, user_email: str, channel_name: str) -> Literal["client", "internal", "unknown"]:
        """
        Determines if a user is internal or client based on their email domain.

        1. If the email ends in a known INTERNAL_DOMAINS → "internal"
        2. If the email matches the client_email_domain for the channel → "client"
        3. Else → "unknown"
        """
        if not user_email or '@' not in user_email:
            return "unknown"

        user_domain = user_email.split('@')[-1].lower()

        # ✅ Global check for internal domains
        if user_domain in INTERNAL_DOMAINS:
            return "internal"

        # 🔁 Fallback: check if the email matches the client's domain from the CSV
        metadata = self.get_metadata_by_channel(channel_name)
        if not metadata:
            return "unknown"

        client_domain = metadata.get("email_domain")
        if client_domain and user_domain == client_domain.lower():
            return "client"

        return "unknown"


# Singleton instance to be used across the application
metadata_loader = MetadataLoader()

# Example usage (for testing or direct script run)
if __name__ == '__main__':
    # Ensure you have a 'channel_metadata.csv' file in the same directory
    # with the headers: channel_name,client_name,client_email_domain,channel_url
    
    # Using the singleton instance
    test_channel = "revops-ai"
    metadata = metadata_loader.get_metadata_by_channel(test_channel)
    if metadata:
        logging.info("Metadata for %s: %s", test_channel, metadata)
    else:
        logging.warning("No metadata found for channel: %s", test_channel)

    # Test get_role
    client_email = "user@revops-ai.com"
    internal_email = "employee@mycompany.com"
    
    client_role = metadata_loader.get_role(client_email, test_channel)
    logging.info("Role for %s in %s: %s", client_email, test_channel, client_role)

    internal_role = metadata_loader.get_role(internal_email, test_channel)
    logging.info("Role for %s in %s: %s", internal_email, test_channel, internal_role)

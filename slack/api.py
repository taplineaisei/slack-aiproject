import os
import logging
import time
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Initialize Slack WebClient
try:
    slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_bot_token)
    logging.info("Slack WebClient initialized successfully.")
except KeyError:
    logging.error("SLACK_BOT_TOKEN not found in environment variables. Please check your .env file.")
    client = None

_channel_id_cache = {}

def get_channel_id_by_name(channel_name: str) -> str | None:
    """
    Fetches the channel ID for a given channel name. Uses a cache to avoid repeated API calls.
    """
    if channel_name in _channel_id_cache:
        return _channel_id_cache[channel_name]
        
    if not client:
        logging.error("Slack client not initialized. Cannot fetch channel ID.")
        return None
        
    try:
        # This will search both public and private channels the bot is in
        for page in client.conversations_list(types="public_channel,private_channel"):
            for channel in page["channels"]:
                if channel["name"] == channel_name:
                    channel_id = channel["id"]
                    _channel_id_cache[channel_name] = channel_id # Cache the result
                    logging.info(f"Found channel ID for #{channel_name}: {channel_id}")
                    return channel_id
    except SlackApiError as e:
        logging.error(f"Error fetching channel list: {e}")
    
    logging.warning(f"Could not find channel ID for #{channel_name}.")
    return None

def get_channel_history(channel_id: str, days_ago: int = 1) -> List[Dict[str, Any]] | None:
    """
    Fetches the message history for a channel for the last N days.
    """
    if not client:
        logging.error("Slack client not initialized. Cannot fetch channel history.")
        return None
    
    try:
        # Calculate the timestamp for N days ago
        oldest_timestamp = (datetime.now() - timedelta(days=days_ago)).timestamp()
        
        response = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest_timestamp),
            limit=1000 # Max limit per page
        )
        
        if response["ok"]:
            # The API returns messages from newest to oldest, so we reverse them for chronological order
            messages = response["messages"]
            messages.reverse()
            logging.info(f"Fetched {len(messages)} messages from channel {channel_id} for the last {days_ago} day(s).")
            return messages
            
    except SlackApiError as e:
        logging.error(f"Error fetching channel history for {channel_id}: {e}")
    return None

def get_user_email(user_id: str, max_retries: int = 3) -> str | None:
    if not client:
        logging.error("Slack client not initialized. Cannot fetch user email.")
        return None
    
    for attempt in range(max_retries):
        try:
            response = client.users_info(user=user_id)
            if response["ok"]:
                # Use .get() for safer access in case 'profile' or 'email' is missing
                return response.get("user", {}).get("profile", {}).get("email")
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                delay = int(e.response.headers.get("Retry-After", 1))
                logging.warning("Rate limited. Retrying after %d seconds...", delay)
                time.sleep(delay)
            else:
                logging.error(f"Error fetching user info for {user_id}: {e}")
                break
        except Exception as e:
            logging.error(f"An unexpected error occurred in get_user_email: {e}")
            break
    logging.error(f"Failed to retrieve email for user {user_id} after {max_retries} attempts.")
    return None

def post_alert(channel_name: str, message: str):
    if not client:
        logging.error("Slack client not initialized. Cannot post alert.")
        return

    try:
        response = client.chat_postMessage(channel=f"#{channel_name}", text=message)
        if not response["ok"]:
            logging.error(f"Failed to post alert to #{channel_name}: {response['error']}")
    except SlackApiError as e:
        logging.error(f"Error posting alert to #{channel_name}: {e}")

def post_summary(channel_name: str, summary_text: str):
    post_alert(channel_name, summary_text)

def build_message_link(channel_id: str, message_ts: str) -> str | None:
    if not client:
        logging.error("Slack client not initialized. Cannot build message link.")
        return None
        
    try:
        response = client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
        if response["ok"]:
            return response["permalink"]
    except SlackApiError as e:
        logging.error(f"Error getting message permalink: {e}")
    return None

if __name__ == '__main__':
    # --- Test get_user_email ---
    test_user_id = "U08TFTK29FA" 
    email = get_user_email(test_user_id)
    if email:
        logging.info(f"Successfully fetched email for user {test_user_id}: {email}")
    else:
        logging.warning(f"Could not fetch email for user {test_user_id}.")

    # --- Test post_alert ---
    logging.info("Testing post_alert to #client-alerts channel.")
    post_alert("client-alerts", "🔥 Test alert from the Slack Monitoring Agent!")

    # --- Test build_message_link ---
    test_channel_id = "C08SW26R552"
    test_message_ts = "1747424716.272029" 
    link = build_message_link(test_channel_id, test_message_ts)
    if link:
        logging.info(f"Successfully created message link: {link}")
    else:
        logging.warning("Failed to create message link.")

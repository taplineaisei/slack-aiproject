import os
import sys
import logging
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from storage.metadata_loader import metadata_loader
from storage.memory import message_memory
from slack.api import get_user_email
from tasks.question_tracker import question_tracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize Slack App
try:
    app = App(token=os.environ["SLACK_BOT_TOKEN"])
    logging.info("Slack App initialized successfully.")
except KeyError:
    logging.error("SLACK_BOT_TOKEN not found in environment variables.")
    app = None

# --- Message Handler ---
@app.message()
def handle_message(message, say):
    """
    Handles incoming messages from channels the bot is a member of.
    """
    # The actual message data can be in the top-level object or nested under a 'message' key for edits
    message_content = message.get("message", message)

    # Basic validation
    if 'user' not in message_content or 'text' not in message_content:
        return # Skip messages without a user or text

    user_id = message_content['user']
    channel_id = message['channel'] # Channel ID is always top-level
    text = message_content['text']

    # Ignore messages from bots
    if message.get("bot_id") or message_content.get("bot_id"):
        return

    # Get channel name from channel ID (requires conversations.info)
    try:
        channel_info = app.client.conversations_info(channel=channel_id)
        if channel_info['ok']:
            channel_name = channel_info['channel']['name']
        else:
            logging.warning(f"Could not retrieve channel name for ID {channel_id}.")
            return
    except Exception as e:
        logging.error(f"Error fetching channel info for {channel_id}: {e}")
        return

    # Check if the channel is one we should monitor
    if not metadata_loader.get_metadata_by_channel(channel_name):
        logging.debug(f"Ignoring message from unmonitored channel: #{channel_name}")
        return

    # Get user email and determine role
    user_email = get_user_email(user_id)
    if not user_email:
        logging.warning(f"Could not determine email for user {user_id} in channel #{channel_name}.")
        return

    user_role = metadata_loader.get_role(user_email, channel_name)
    
    # Log the processed message details
    logging.info(f"Message received in #{channel_name} | User: {user_email} (Role: {user_role}) | Text: '{text}'")
    
    # Create a structured message object
    message_to_store = {
        "timestamp": message_content["ts"],
        "thread_ts": message.get("thread_ts", message_content.get("thread_ts")), # Ensure thread_ts is captured
        "text": text,
        "user_id": user_id,
        "user_role": user_role,
        "client_msg_id": message_content.get("client_msg_id"), # Pass this through
        "channel_id": channel_id, # Pass this through for the question tracker
        "channel_name": channel_name # Add channel name for later lookup
    }

    # Append to the in-memory buffer for this channel
    message_memory.append(channel_id, message_to_store)

    # Notify the question tracker of the new message
    question_tracker.handle_new_message(message_to_store)

def start_listening():
    """
    Starts the Slack Socket Mode listener.
    """
    if not app or "SLACK_APP_TOKEN" not in os.environ:
        logging.error("Slack App or SLACK_APP_TOKEN not configured. Aborting listener start.")
        return

    try:
        logging.info("Starting Slack listener...")
        SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
    except Exception as e:
        logging.critical(f"A critical error occurred in the Slack listener: {e}", exc_info=True)

if __name__ == "__main__":
    # To test this, run the script and then send a message in a channel
    # that the bot has been invited to.
    # Make sure your .env file has both SLACK_BOT_TOKEN and SLACK_APP_TOKEN.
    start_listening()

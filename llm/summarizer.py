import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI

from slack.api import get_channel_history, get_user_email, post_summary
from storage.metadata_loader import metadata_loader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize OpenAI client
try:
    openai_api_key = os.environ["OPENAI_API_KEY"]
    client = OpenAI(api_key=openai_api_key)
    logging.info("OpenAI client for summarizer initialized successfully.")
except KeyError:
    logging.error("OPENAI_API_KEY not found in environment variables.")
    client = None

class Summarizer:
    def __init__(self):
        if not client:
            raise ValueError("OpenAI client is not initialized. Check your API key.")
        self.client = client
        self.user_cache = {} # Cache user roles to avoid repeated API calls

    def _get_user_role(self, user_id: str, channel_name: str) -> str:
        """Gets user role, using a cache to avoid redundant lookups."""
        if user_id in self.user_cache:
            return self.user_cache[user_id]
        
        email = get_user_email(user_id)
        if not email:
            return "Unknown" # Should not happen often
            
        role = metadata_loader.get_role(email, channel_name)
        self.user_cache[user_id] = role
        return role

    def _format_dialogue_for_summary(self, messages: List[Dict[str, Any]], channel_name: str) -> str:
        """Formats message history into a readable dialogue for the summary prompt."""
        dialogue = []
        for msg in messages:
            user_id = msg.get("user")
            text = msg.get("text")
            
            if not user_id or not text or msg.get("bot_id"):
                continue

            role = self._get_user_role(user_id, channel_name)
            # Convert timestamp to a readable time format (e.g., 9:42 AM)
            msg_time = datetime.fromtimestamp(float(msg['ts'])).strftime('%-I:%M %p')
            dialogue.append(f"{msg_time} - {role.title()}: {text}")
            
        return "\n".join(dialogue)

    def generate_daily_summary(self, channel_id: str, channel_name: str):
        """
        Generates and posts a daily summary for a given channel.
        """
        logging.info(f"Generating daily summary for channel: {channel_name} ({channel_id})")
        self.user_cache.clear() # Clear cache for each new summary run

        # 1. Fetch message history
        messages = get_channel_history(channel_id, days_ago=1)
        if not messages:
            logging.info(f"No messages found in the last 24 hours for {channel_name}. Skipping summary.")
            return

        # 2. Format dialogue
        dialogue = self._format_dialogue_for_summary(messages, channel_name)
        if not dialogue:
            logging.info(f"Dialogue for {channel_name} is empty after formatting. Skipping summary.")
            return

        # 3. Send to LLM
        system_prompt = """
You are a helpful AI assistant tasked with summarizing a day of Slack conversations between a client and a support team.
Based on the provided dialogue, generate a concise summary in markdown format.
The summary should include the following sections:
- **Key Concerns Raised**: Any problems or issues the client brought up.
- **Praise & Positive Feedback**: Any compliments or positive remarks from the client.
- **Unresolved Issues**: Any open questions or problems that were not resolved by the end of the day.
- **Key Action Items**: Any clear next steps for the team.

If a section has no relevant information, omit it from the summary.
Here is the conversation:
"""
        try:
            logging.info(f"Sending dialogue for {channel_name} to GPT-4o for summarization...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": dialogue}
                ],
                temperature=0.2,
            )
            
            summary_text = response.choices[0].message.content
            logging.info(f"Successfully received summary for {channel_name}.")

            # 4. Post summary
            client_name = metadata_loader.get_metadata_by_channel(channel_name).get("client_name", channel_name)
            final_post = f"📝 *Daily Summary for {client_name} - {datetime.now().strftime('%B %d, %Y')}*\n\n{summary_text}"
            post_summary("client-summaries", final_post)
            logging.info(f"Posted daily summary for {channel_name} to #client-summaries.")

        except Exception as e:
            logging.error(f"An unexpected error occurred during summarization for {channel_name}: {e}", exc_info=True)

# Singleton instance
summarizer = Summarizer()

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MessageMemory:
    """
    Manages a sliding window buffer of messages for each channel.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MessageMemory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            # defaultdict simplifies appending to a list for a new channel
            self.buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            self._initialized = True

    def append(self, channel_id: str, message: Dict[str, Any]):
        """
        Appends a message to the buffer for a given channel.
        Handles retries and edits by checking client_msg_id.
        """
        message['received_at'] = datetime.now()
        client_msg_id = message.get('client_msg_id')

        # Only perform deduplication if a client_msg_id is present
        if client_msg_id:
            for i, msg in enumerate(self.buffers[channel_id]):
                if msg.get('client_msg_id') == client_msg_id:
                    self.buffers[channel_id][i] = message
                    logging.info(f"Updated an existing message in buffer for channel {channel_id}.")
                    return
        
        # If no client_msg_id or no match was found, append as a new message
        self.buffers[channel_id].append(message)
        logging.info(f"Appended new message to buffer for channel {channel_id}. Buffer size: {len(self.buffers[channel_id])}")
    
    def get_and_clear_buffer(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all messages for a channel and clears its buffer.

        Args:
            channel_id: The ID of the channel.

        Returns:
            A list of messages for the channel.
        """
        messages = self.buffers.pop(channel_id, [])
        logging.info(f"Retrieved and cleared buffer for channel {channel_id}. {len(messages)} messages taken.")
        return messages

    def get_last_message_time(self, channel_id: str) -> datetime | None:
        """
        Gets the timestamp of the most recent message in a channel's buffer.

        Args:
            channel_id: The ID of the channel.

        Returns:
            The datetime of the last message, or None if the buffer is empty.
        """
        if self.buffers[channel_id]:
            return self.buffers[channel_id][-1]['received_at']
        return None

# Singleton instance to be used across the application
message_memory = MessageMemory()

if __name__ == '__main__':
    # Example usage for testing
    test_channel = "C12345"
    
    # 1. Append messages
    msg1 = {"user": "U1", "text": "Hello", "ts": "1629882211.000100", "client_msg_id": "id1"}
    msg2 = {"user": "U2", "text": "Hi there", "ts": "1629882212.000200", "client_msg_id": "id2"}
    message_memory.append(test_channel, msg1)
    message_memory.append(test_channel, msg2)

    # 2. Check last message time
    last_time = message_memory.get_last_message_time(test_channel)
    logging.info(f"Last message time for {test_channel}: {last_time}")
    
    # 3. Edit a message
    msg1_edited = {"user": "U1", "text": "Hello world", "ts": "1629882211.000100", "client_msg_id": "id1"}
    message_memory.append(test_channel, msg1_edited)
    
    # 4. Get and clear buffer
    buffered_messages = message_memory.get_and_clear_buffer(test_channel)
    logging.info(f"Retrieved messages: {buffered_messages}")
    logging.info(f"Buffer for {test_channel} is now empty: {not message_memory.buffers[test_channel]}")

    # Verify buffer is cleared
    last_time_after_clear = message_memory.get_last_message_time(test_channel)
    logging.info(f"Last message time for {test_channel} after clearing: {last_time_after_clear}")

import logging
import time
import threading
from dotenv import load_dotenv

from slack.listener import start_listening
from tasks.scheduler import start_scheduler, run_daily_summaries

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main entrypoint for the Slack Monitoring Agent.
    Initializes and starts all the necessary components.
    """
    # Load environment variables from .env file
    load_dotenv()
    logging.info("Environment variables loaded.")

    # Start the background task scheduler
    # This will handle analyzing message buffers, checking for unanswered questions, etc.
    start_scheduler()
    
    # Start the Slack listener in a separate thread
    # This continuously listens for new messages from Slack
    logging.info("Starting Slack listener in a background thread...")
    listener_thread = threading.Thread(target=start_listening, daemon=True)
    listener_thread.start()
    logging.info("Slack listener is running.")

    # Keep the main thread alive to allow background threads to run
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutdown signal received. Exiting.")

if __name__ == "__main__":
    main()

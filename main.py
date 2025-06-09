import logging
import os
import sys
import threading
from dotenv import load_dotenv
from flask import Flask

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# --- Load environment variables and configure logging first ---
# This ensures that all modules have access to env variables and logging is set up.
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("--- Application Starting Up ---")

# Now import the other modules
from slack.listener import start_listening
from tasks.scheduler import (
    start_scheduler,
    INACTIVITY_THRESHOLD_MINUTES,
    SCHEDULER_INTERVAL_MINUTES,
    QUESTION_EXPIRY_INTERVAL_MINUTES
)

# --- Log the loaded configuration for debugging ---
logging.info("Scheduler Configuration Loaded:")
logging.info(f"  - Inactivity Threshold: {INACTIVITY_THRESHOLD_MINUTES} minutes")
logging.info(f"  - Scheduler Interval: {SCHEDULER_INTERVAL_MINUTES} minutes")
logging.info(f"  - Question Expiry Interval: {QUESTION_EXPIRY_INTERVAL_MINUTES} minutes")

# --- Flask App for Render Health Checks ---
app = Flask(__name__)

@app.route('/')
def health_check():
    """
    This endpoint is used by Render to check if the service is alive.
    """
    return "OK", 200

def run_background_tasks():
    """
    Starts the Slack listener and the scheduler in background threads.
    """
    # Start the background task scheduler
    start_scheduler()
    
    # Start the Slack listener in a separate thread
    logging.info("Starting Slack listener in a background thread...")
    listener_thread = threading.Thread(target=start_listening, daemon=True)
    listener_thread.start()
    logging.info("Slack listener is running.")

def main():
    """
    Main entrypoint for the Slack Monitoring Agent.
    """
    logging.info("Starting background tasks...")
    run_background_tasks()

    # The Flask app will be run by Gunicorn in production (see render.yaml)
    # This block is for local development if you want to run it directly.
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)

# Run the main function to set up background tasks before the server starts
main()

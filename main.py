import logging
import os
import threading
from dotenv import load_dotenv
from flask import Flask

from slack.listener import start_listening
from tasks.scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    load_dotenv()
    logging.info("Environment variables loaded.")
    run_background_tasks()

    # The Flask app will be run by Gunicorn in production (see render.yaml)
    # This block is for local development if you want to run it directly.
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)

# Run the main function to set up background tasks before the server starts
main()

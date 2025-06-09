import logging
import os
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

from storage.memory import message_memory
from llm.trigger_engine import trigger_engine
from slack.api import post_alert, build_message_link, get_channel_id_by_name
from storage.metadata_loader import metadata_loader
from tasks.question_tracker import question_tracker
from llm.summarizer import summarizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# How long a channel must be inactive before we process its messages
INACTIVITY_THRESHOLD_MINUTES = float(os.environ.get("INACTIVITY_THRESHOLD_MINUTES", 5)) # Default to 5 minutes
# How often the scheduler checks for inactive channels (in minutes)
SCHEDULER_INTERVAL_MINUTES = float(os.environ.get("SCHEDULER_INTERVAL_MINUTES", 1)) # Default to 1 minute
# How often the scheduler checks for expired questions (in minutes)
QUESTION_EXPIRY_INTERVAL_MINUTES = float(os.environ.get("QUESTION_EXPIRY_INTERVAL_MINUTES", 1)) # Default to 1 minute

def analyze_inactive_channels():
    """
    Checks for channels that have been inactive for a specified duration,
    sends their message buffers to the trigger engine, and posts alerts.
    """
    logging.info("Scheduler running: Checking for inactive channels...")
    now = datetime.now()
    
    # Iterate over a copy of the keys to allow modification during iteration
    for channel_id in list(message_memory.buffers.keys()):
        last_message_time = message_memory.get_last_message_time(channel_id)
        
        if last_message_time and (now - last_message_time > timedelta(minutes=INACTIVITY_THRESHOLD_MINUTES)):
            logging.info(f"Channel {channel_id} has been inactive for over {INACTIVITY_THRESHOLD_MINUTES} minutes. Processing buffer.")
            
            # Get all messages and clear the buffer for this channel
            messages_to_process = message_memory.get_and_clear_buffer(channel_id)
            
            if not messages_to_process:
                continue

            # --- Handle Triggers ---
            # All messages in this batch are from the same channel, so we can get the name from the first one.
            channel_name = messages_to_process[0].get("channel_name", "unknown_channel")
            channel_metadata = metadata_loader.get_metadata_by_channel(channel_name)
            client_name = channel_metadata.get("client_name", "An unknown client") if channel_metadata else "An unknown client"
            first_message_ts = messages_to_process[0]['timestamp']
            message_link = build_message_link(channel_id, first_message_ts)

            # Send the batch to the trigger engine for analysis
            analysis = trigger_engine.analyze_message_batch(messages_to_process)
            
            if not analysis:
                logging.error(f"Analysis failed for channel {channel_id}.")
                continue

            # --- Handle Triggers ---
            if analysis.get("is_fire") and analysis.get("fire_text"):
                alert_text = (
                    f"🔥 Client Fire Detected for *{client_name}*!\n\n"
                    f"> {analysis['fire_text']}\n\n"
                    f"<{message_link}|Jump to conversation>"
                )
                post_alert("client-alerts", alert_text)

            if analysis.get("is_testimonial") and analysis.get("testimonial_text"):
                alert_text = (
                    f"🌟 New Testimonial from *{client_name}*!\n\n"
                    f"> {analysis['testimonial_text']}\n\n"
                    f"<{message_link}|Jump to conversation>"
                )
                post_alert("testimonials", alert_text)

            # Handle questions
            if analysis.get("is_question") and analysis.get("questions"):
                logging.info(f"Questions detected for {client_name}. Handing off to question tracker.")
                question_tracker.add_unanswered_questions(
                    analysis["questions"],
                    channel_id,
                    channel_name
                )

def run_daily_summaries():
    """
    Iterates through all monitored channels and triggers the daily summary generation.
    """
    logging.info("Scheduler running: Kicking off end-of-day summaries.")
    monitored_channels = metadata_loader.metadata.keys()
    
    for channel_name in monitored_channels:
        channel_id = get_channel_id_by_name(channel_name)
        if channel_id:
            try:
                summarizer.generate_daily_summary(channel_id, channel_name)
            except Exception as e:
                logging.error(f"Failed to generate summary for {channel_name}: {e}", exc_info=True)
        else:
            logging.warning(f"Could not generate summary for '{channel_name}' because its ID could not be found.")

def start_scheduler():
    """Initializes and starts the APScheduler."""
    scheduler = BackgroundScheduler()
    pst_timezone = pytz.timezone("America/Los_Angeles")

    # Job 1: Analyze message buffers
    scheduler.add_job(
        analyze_inactive_channels,
        'interval',
        seconds=SCHEDULER_INTERVAL_MINUTES * 60
    )
    # Job 2: Check for expired questions
    scheduler.add_job(
        question_tracker.check_for_expired_questions,
        'interval',
        seconds=QUESTION_EXPIRY_INTERVAL_MINUTES * 60
    )
    # Job 3: Run daily summaries at 6:00 PM PST
    scheduler.add_job(
        run_daily_summaries,
        'cron',
        hour=18,
        minute=0,
        timezone=pst_timezone
    )
    try:
        scheduler.start()
        logging.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs.")
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shut down.")

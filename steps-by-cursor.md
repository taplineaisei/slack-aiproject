Phase 1: Foundations
Step 1: Project Setup & Dependencies: We'll start by creating the directory structure and populating the requirements.txt file with all the necessary libraries (openai, slack_sdk, slack_bolt, python-dotenv, apscheduler).
Step 2: Configuration & Metadata Loading: We'll implement storage/metadata_loader.py. This is a crucial first step as it will load the channel_metadata.csv file, which is essential for identifying which channels to monitor and who the clients are.
Step 3: Basic Slack API Utilities: We will create the slack/api.py module and implement the helper functions that don't depend on other logic yet, such as get_user_email and build_message_link. This allows us to verify our Slack API credentials early on.
Phase 2: Message Ingestion and Processing
Step 4: Slack Message Listener: We'll implement the core of the bot in slack/listener.py. We will set up the Slack SocketModeHandler to listen for new messages in channels. We'll integrate the metadata_loader to determine if a message is from a monitored channel and classify the sender as client or internal.
Step 5: In-Memory Message Buffering: Next, we'll build storage/memory.py. This component will create a sliding window of messages, holding onto them for a 5-minute interval for each channel. This is the core of our "batching" logic. We'll hook this into the listener from Step 4.
Phase 3: AI-Powered Analysis and Alerting
Step 6: LLM Trigger Engine: This is where the magic happens. We'll create llm/trigger_engine.py. This module will take the 5-minute message batches from our memory store, format them into a clean dialogue, and send them to the GPT-4o API to detect "fires," "testimonials," and "questions."
Step 7: Real-time Alerts: We'll connect the trigger_engine to slack/api.py. When the LLM detects a "fire" or a "testimonial," we'll implement the post_alert function to immediately send a notification to the #client-alerts or #testimonials channels.
Phase 4: Advanced Features and Scheduling
Step 8: Unanswered Question Tracking: We'll build tasks/question_tracker.py. This component will keep a record of questions identified by the LLM, along with a 30-minute response deadline. It will also need to monitor message threads to see if a question gets answered by an internal team member.
Step 9: Background Scheduler: We'll implement tasks/scheduler.py using APScheduler. We will set up a recurring job that runs every minute to check for any unanswered questions that have passed their deadline and send an alert.
Step 10: End-of-Day Summaries: We'll create llm/summarizer.py. This will fetch the day's messages for each client channel, use GPT-4o to create a concise summary, and post it to the #client-summaries channel. We will add a daily scheduled job for this in our scheduler.
Phase 5: Finalization
Step 11: Main Entrypoint: We'll tie everything together in main.py. This script will be responsible for loading the environment variables, initializing all our services (Slack listener, scheduler, etc.), and starting the application.
Step 12: Deployment: Finally, we'll create the render.yaml file for easy deployment and a README.md for project documentation.
This plan breaks the project down into manageable, logical pieces. We can tackle them one by one, ensuring each component works correctly before moving to the next.
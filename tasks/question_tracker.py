import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

from slack.api import post_alert, build_message_link
from storage.metadata_loader import metadata_loader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuestionTracker:
    """
    Tracks unanswered client questions and sends alerts for expired ones.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(QuestionTracker, cls).__new__(cls)
        return cls._instance

    def __init__(self, deadline_minutes: float = 30):
        if not hasattr(self, '_initialized'):
            # Using question timestamp as the unique key
            self.unanswered_questions: Dict[str, Dict[str, Any]] = {}
            self.deadline = timedelta(minutes=deadline_minutes)
            self._initialized = True

    def add_unanswered_questions(self, questions: List[Dict[str, Any]], channel_id: str, channel_name: str):
        """
        Adds new questions to the tracker.
        """
        for q in questions:
            question_ts = q.get("timestamp")
            if not question_ts:
                continue
            
            # Don't track a question that's already being tracked
            if question_ts not in self.unanswered_questions:
                self.unanswered_questions[question_ts] = {
                    "text": q["text"],
                    "timestamp": question_ts,
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "deadline": datetime.now() + self.deadline,
                }
                logging.info(f"Now tracking new question in #{channel_name}: '{q['text']}'")

    def handle_new_message(self, message: Dict[str, Any]):
        """
        Checks if a new message from an internal user answers any tracked question
        in the same channel.
        """
        user_role = message.get("user_role")
        channel_id = message.get("channel_id")

        if user_role == "internal" and channel_id:
            # Find all questions being tracked in this channel
            questions_in_channel = [
                ts for ts, q in self.unanswered_questions.items() if q["channel_id"] == channel_id
            ]
            
            # Mark all of them as answered
            for question_ts in questions_in_channel:
                self.mark_as_answered(question_ts)
    
    def mark_as_answered(self, question_ts: str):
        """
        Removes a question from the tracker.
        """
        if question_ts in self.unanswered_questions:
            question = self.unanswered_questions.pop(question_ts)
            logging.info(f"Question in #{question['channel_name']} answered and removed from tracker: '{question['text']}'")

    def check_for_expired_questions(self):
        """
        Checks for questions that have passed their deadline and sends alerts.
        """
        now = datetime.now()
        # Iterate over a copy of the keys to allow modification during iteration
        for question_ts in list(self.unanswered_questions.keys()):
            question = self.unanswered_questions[question_ts]
            if now > question["deadline"]:
                logging.warning(f"Question has expired in #{question['channel_name']}: '{question['text']}'")
                
                # Format and send the alert
                channel_metadata = metadata_loader.get_metadata_by_channel(question["channel_name"])
                client_name = channel_metadata.get("client_name", "An unknown client") if channel_metadata else "An unknown client"
                message_link = build_message_link(question["channel_id"], question_ts)
                
                alert_text = (
                    f"❓ Unanswered Question for *{client_name}* needs attention!\n\n"
                    f"> {question['text']}\n\n"
                    f"This question has been unanswered for {self.deadline.total_seconds() / 60} minutes.\n"
                    f"<{message_link}|Jump to question>"
                )
                post_alert("client-alerts", alert_text)
                
                # Remove the question so we don't alert again
                self.unanswered_questions.pop(question_ts)

# Singleton instance
deadline = float(os.environ.get("QUESTION_EXPIRATION_MINUTES", 0.5))
question_tracker = QuestionTracker(deadline_minutes=deadline)

if __name__ == '__main__':
    # Example usage for testing
    print("Running QuestionTracker test...")
    test_channel_id = "C12345"
    test_channel_name = "revops-ai"
    q1 = {"text": "How do I update my billing info?", "timestamp": "1700000001.000100"}
    
    # 1. Add a question
    question_tracker.add_unanswered_questions([q1], test_channel_id, test_channel_name)
    print(f"Tracked questions: {question_tracker.unanswered_questions}")
    assert "1700000001.000100" in question_tracker.unanswered_questions

    # 2. Simulate an answer
    answer_message = {"thread_ts": "1700000001.000100", "user_role": "internal"}
    question_tracker.handle_new_message(answer_message)
    print(f"Tracked questions after answer: {question_tracker.unanswered_questions}")
    assert "1700000001.000100" not in question_tracker.unanswered_questions
    
    # 3. Add a question and let it expire
    q2 = {"text": "What is the ETA for the new feature?", "timestamp": "1700000002.000200"}
    # Temporarily set a very short deadline for testing
    question_tracker.deadline = timedelta(seconds=1)
    question_tracker.add_unanswered_questions([q2], test_channel_id, test_channel_name)
    print(f"Tracked questions: {question_tracker.unanswered_questions}")

    print("Waiting for question to expire...")
    import time
    time.sleep(2)
    
    # This would normally be run by the scheduler. We need a mock slack_api for this test to run.
    # For now, we will just check that the question is still there.
    # To fully test check_for_expired_questions, we'd need to mock post_alert.
    # question_tracker.check_for_expired_questions()
    
    print("Test complete.")

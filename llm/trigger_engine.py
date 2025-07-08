import os
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize OpenAI client
try:
    openai_api_key = os.environ["OPENAI_API_KEY"]
    client = OpenAI(api_key=openai_api_key)
    logging.info("OpenAI client initialized successfully.")
except KeyError:
    logging.error("OPENAI_API_KEY not found in environment variables.")
    client = None

class TriggerEngine:
    """
    Analyzes message batches using an LLM to detect specific triggers.
    """
    def __init__(self):
        if not client:
            raise ValueError("OpenAI client is not initialized. Check your API key.")
        self.client = client

    def _format_dialogue(self, messages: List[Dict[str, Any]]) -> str:
        """Formats a list of message objects into a readable dialogue string."""
        dialogue = []
        for msg in messages:
            role = "Client" if msg.get("user_role") == "client" else "Team"
            text = msg.get("text", "")
            # Include the timestamp in the dialogue for the AI to see
            dialogue.append(f"{role} (timestamp: {msg.get('timestamp')}): {text}")
        return "\n".join(dialogue)

    def analyze_message_batch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """
        Sends a message batch to the LLM for analysis and returns the structured output.

        Args:
            messages: A list of message dictionaries from the memory buffer.

        Returns:
            A dictionary with analysis results, or None on failure.
        """
        if not messages:
            return None

        dialogue = self._format_dialogue(messages)
        
        system_prompt = """
You are a helpful AI assistant monitoring a client communication channel on Slack.
Your task is to analyze a conversation and identify three things from messages sent by the **Client** only:
1.  **Client Fire**: Is the **Client** expressing urgent, negative sentiment?
2.  **Testimonial**: Is the **Client** expressing strong, positive sentiment or reporting meaningful wins, milestones, or client results? This includes praise or mentions of signing a client, landing a deal, closing a retainer, etc.
3.  **Client Questions**: List any explicit questions the **Client** has asked that have not yet been answered by the team.

**IMPORTANT**: Only analyze messages where the role is "Client". Ignore any fires, testimonials, or questions from the "Team".
...


Here is an example:
---
**Input Dialogue:**
Client (timestamp: 101): This is unacceptable, the system is down again!
Team (timestamp: 102): I'm so sorry, looking into this now. What seems to be the issue from your end?
Client (timestamp: 103): Also, I wanted to say that the new update is fantastic! Really great work.
Client (timestamp: 104): Can you tell me when the fix will be deployed?
---
**Expected JSON Output:**
{
  "is_fire": true,
  "fire_text": "This is unacceptable, the system is down again!",
  "is_testimonial": true,
  "testimonial_text": "Also, I wanted to say that the new update is fantastic! Really great work.",
  "is_question": true,
  "questions": [
    { "text": "Can you tell me when the fix will be deployed?", "timestamp": "104" }
  ]
}
---

Please respond ONLY with a valid JSON object in the format shown in the example. For each question, find the corresponding message in the dialogue and copy its 'timestamp' value into the 'timestamp' field.
"""

        try:
            logging.info("Sending dialogue to GPT-4o for analysis...")
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": dialogue}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            
            # Add original message objects to question analysis for later use
            analysis_result = json.loads(response.choices[0].message.content)
            logging.info(f"Successfully received and parsed analysis from GPT-4o: {analysis_result}")
            if analysis_result.get("questions"):
                for question in analysis_result["questions"]:
                    # Find the original message to preserve all its data
                    original_message = next((msg for msg in messages if msg["timestamp"] == question.get("timestamp")), None)
                    if original_message:
                        question["original_message"] = original_message

            return analysis_result

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON from LLM response: {e}")
            logging.error(f"Raw LLM Response: {response.choices[0].message.content}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during LLM analysis: {e}", exc_info=True)
            return None

# Singleton instance
trigger_engine = TriggerEngine()

if __name__ == '__main__':
    # Example usage for testing
    print("Running TriggerEngine test...")
    # This sample conversation contains a fire, a testimonial, and a question.
    sample_messages = [
        {'timestamp': '1', 'user_role': 'client', 'text': 'I am really frustrated, this feature is completely broken!'},
        {'timestamp': '2', 'user_role': 'team', 'text': 'I am so sorry to hear that, let me look into it right away.'},
        {'timestamp': '3', 'user_role': 'client', 'text': 'Okay, but how do I get a refund for this month?'},
        {'timestamp': '4', 'user_role': 'client', 'text': 'Separately, I just have to say your support on that other ticket was amazing. You guys are lifesavers!'},
        {'timestamp': '5', 'user_role': 'team', 'text': 'I can help with the refund process. As for the other issue, thank you so much for the kind words!'}
    ]
    
    analysis = trigger_engine.analyze_message_batch(sample_messages)
    
    if analysis:
        print("\n--- Analysis Result ---")
        print(json.dumps(analysis, indent=2))
        print("-----------------------\n")
    else:
        print("Analysis failed.")

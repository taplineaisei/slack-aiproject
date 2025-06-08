🧠 Cursor AI Project Instructions
Title: Real-Time Slack Monitoring Agent for Client Channels
Deployment Target: Render
Goal: Build a real-time Slack AI bot that observes client conversations and does four things:

🔥 Detects urgent, negative “client fire” messages

❓ Tracks unanswered client questions

🌟 Flags testimonial-worthy praise

📝 Sends daily summaries to internal teams

📜 High-Level Project Context
Business teams often manage client communications in dedicated Slack channels (e.g. revops-ai)

This bot listens to those channels, analyzes message windows using GPT-4o, and automates critical team workflows

This specific implementation is meant for demo purposes using the revops-ai test channel and three internal output channels:

#client-alerts → fires

#testimonials → strong praise

#client-summaries → daily digests

📁 Required Directory Structure
Cursor, create the following file structure:

pgsql
Copy
Edit
.
├── main.py
├── slack/
│   ├── listener.py
│   ├── api.py
│   ├── utils.py
├── llm/
│   ├── trigger_engine.py
│   ├── summarizer.py
├── storage/
│   ├── memory.py
│   ├── metadata_loader.py
├── tasks/
│   ├── question_tracker.py
│   ├── scheduler.py
├── channel_metadata.csv
├── requirements.txt
├── render.yaml
├── .env (local only)
└── README.md
📊 1. channel_metadata.csv (Reference Format)
Cursor, load this CSV at runtime. Example row:

csv
Copy
Edit
channel_name,client_name,client_email_domain,channel_url
revops-ai,Revops AI,revops-ai.com,https://slack.com/app_redirect?channel=C08SW26R552
Important Notes:

This file maps Slack channels to clients and is critical for:

Validating whether a channel should be monitored

Detecting which users are clients (via email domain)

Formatting alert messages with client names and click-through links

Cursor should throw a warning if an incoming message is from a channel not found in this file.

🧠 2. main.py (Entrypoint)
Cursor, this script must:

Load .env values:

SLACK_APP_TOKEN

SLACK_BOT_TOKEN

OPENAI_API_KEY

Start the Slack Socket Mode listener

Run the following background workers:

Message batching and window manager

Question tracker expiry checker

End-of-day summarizer at 6:00 PM PST

Watch out for:

Slack token load failures

.env missing required keys

Use logging for startup and worker status messages

🧵 3. slack/listener.py — Slack Ingestion
Connect via slack_bolt using Socket Mode (SLACK_APP_TOKEN)

Subscribe to:

message.channels

message.groups

For each message:

Use Slack API to get the user's email

Use metadata_loader.py to classify user as:

client if their email domain matches client_email_domain

internal otherwise

Append the message to the rolling buffer using memory.append(channel_id, message_dict)

Watch out for:

user_id lookup failures (rate limits or bot lacks users:read.email)

Messages with no text (file shares, reactions — skip them)

Bot messages — ignore

📦 4. storage/memory.py — 5-Min Message Batching
Cursor, implement a sliding window buffer for each channel.

Every channel keeps a rolling list of recent messages

Every 60 seconds:

If a channel has had no new messages for 5+ minutes:

Consolidate those messages into a batch

Send to llm/trigger_engine.py

Key considerations:

Preserve ts, text, user_role, thread_ts (for question tracking)

Include threading context if possible (for later detection)

Deduplicate edited messages

🧠 5. llm/trigger_engine.py — Trigger Detection via GPT
Cursor, for each 5-min message batch:

Format messages into a readable dialogue (Client: and Team:)

Send one GPT-4o call with the entire window

Parse the LLM response to return:

json
Copy
Edit
{
  "fire": true/false,
  "testimonial": true/false,
  "questions": [
    { "text": "...", "ts": "...", "user_id": "..." }
  ]
}
If any field is true:

Fire → call slack/api.py.post_alert('client-alerts', message)

Testimonial → call slack/api.py.post_alert('testimonials', message)

Questions → register them in question_tracker.py

Error handling:

GPT timeouts

LLM failure → retry once, then log the window and skip

⏳ 6. tasks/question_tracker.py
Track unanswered client questions flagged by the LLM

For each:

Save: channel_id, ts, question_text, deadline = now + 30min

Monitor incoming messages in that channel:

If an internal user replies in the same thread or after, mark as answered

If deadline passes with no answer, send alert to client-alerts

Watch out for:

Duplicate question detection

Edge cases where a message thread is resolved via emoji or non-text reply — skip those

📝 7. llm/summarizer.py
At 6:00 PM PST:

Load all messages from each monitored channel for the last 24h

Format into structured dialogue:

makefile
Copy
Edit
9:42 AM - Client: Hey what's the status?
9:43 AM - Team: Here's the update...
Send to GPT-4o for a structured daily summary

Summary should include:

Concerns raised

Praise

Unresolved issues

Action items

Post to client-summaries via slack/api.py

🔁 8. tasks/scheduler.py
Use APScheduler or similar to:

Run the daily summary once per day

Run the question tracker expiration check every 60 seconds

Watch out for:

Timezone mismatch (ensure PST for the summary)

Skipping EOD if no messages present

📬 9. slack/api.py
Cursor, create helper functions to interact with Slack:

get_user_email(user_id) — returns email (with retry)

post_alert(channel_name, message) — posts to #client-alerts, #testimonials, etc.

post_summary(channel_name, text) — posts EOD summary

build_message_link(channel_id, ts) — builds Slack URL to deep-link message

Watch out for:

Rate limits — retry on 429

Ensure alerts go to correct channel using plain channel_name, not ID

🔗 10. storage/metadata_loader.py
Load channel_metadata.csv at startup

Build mapping:

python
Copy
Edit
{
  "revops-ai": {
    "client_name": "Revops AI",
    "email_domain": "revops-ai.com",
    "channel_url": "https://slack.com/app_redirect?channel=C08SW26R552"
  }
}
Provide lookup functions:

get_metadata_by_channel(channel_name)

get_role(user_email, channel_name)

🛠️ 11. render.yaml — for 1-click deploy on Render
yaml
Copy
Edit
services:
  - type: web
    name: slack-gpt-monitor
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: SLACK_APP_TOKEN
        sync: false
      - key: SLACK_BOT_TOKEN
        sync: false
      - key: OPENAI_API_KEY
        sync: false
📦 12. requirements.txt
nginx
Copy
Edit
openai
slack_sdk
slack_bolt
python-dotenv
schedule
apscheduler
🔐 13. .env (Local Testing)
Cursor, do not commit this. Format:

ini
Copy
Edit
SLACK_APP_TOKEN=xapp-...
SLACK_BOT_TOKEN=xoxb-...
OPENAI_API_KEY=sk-...
These should be manually added as secrets in the Render dashboard.

✅ Final Notes for Cursor AI Agent
This app should run continuously on Render without crashes

Use logging liberally in each module

Catch and log all exceptions in GPT, Slack API, and scheduler tasks

Only act on messages from revops-ai for now (per metadata)

Internal channels:

client-alerts

testimonials

client-summaries


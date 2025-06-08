# Real-Time Slack Monitoring Agent

This project is an AI-powered Slack bot designed to monitor client communication channels in real-time. It uses GPT-4o to analyze conversations and automate key workflows for customer-facing teams.

## Features

-   **🔥 Urgent Message Detection**: Identifies and alerts the team to urgent or negative client messages ("fires").
-   **🌟 Testimonial Flagging**: Captures and saves positive client feedback and testimonials.
-   **❓ Unanswered Question Tracking**: Monitors client questions and sends alerts if they remain unanswered for 30 minutes.
-   **📝 Daily Summaries**: Posts a concise summary of each client channel's activity to an internal channel at the end of each day.

## Project Structure

```
.
├── main.py
├── slack/
│   ├── listener.py
│   ├── api.py
│   └── __init__.py
├── llm/
│   ├── trigger_engine.py
│   ├── summarizer.py
│   └── __init__.py
├── storage/
│   ├── memory.py
│   ├── metadata_loader.py
│   └── __init__.py
├── tasks/
│   ├── question_tracker.py
│   ├── scheduler.py
│   └── __init__.py
├── channel_metadata.csv
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

## Local Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tylervu12/slack-ai
    cd slack-ai
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    -   Copy the `.env.example` file to `.env`: `cp .env.example .env`
    -   Add your API keys and tokens to the `.env` file:
        -   `SLACK_APP_TOKEN`: Your Slack App-Level Token (starts with `xapp-`).
        -   `SLACK_BOT_TOKEN`: Your Slack Bot User OAuth Token (starts with `xoxb-`).
        -   `OPENAI_API_KEY`: Your OpenAI API key.

5.  **Configure Slack Bot:**
    -   Go to your Slack App's configuration page (`api.slack.com/apps`).
    -   **Enable Socket Mode**.
    -   Under **Event Subscriptions**, enable events and subscribe to `message.channels` and `message.groups`.
    -   Under **OAuth & Permissions**, ensure your bot has the following scopes:
        -   `channels:history`
        -   `groups:history`
        -   `users:read`
        -   `users:read.email`
        -   `chat:write`

6.  **Run the application:**
    ```bash
    python main.py
    ```

## Deployment on Render

This project is configured for easy deployment on [Render](https://render.com/).

1.  **Create a new "Background Worker"** on Render and connect it to your GitHub repository.
2.  Render will automatically detect the `render.yaml` file.
3.  Under the **Environment** tab, add your secrets (`SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, `OPENAI_API_KEY`) as secret files or environment variables.
4.  Deploy! The worker will start, and the bot will be live.

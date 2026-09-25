"""Shared Groq client setup for chatbot.py and server.py."""

import os

import groq

MODEL = "openai/gpt-oss-120b"
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_env(path=os.path.join(ROOT, ".env")):
    """Load KEY=VALUE lines from .env into os.environ (existing vars win)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def make_client():
    """Return a Groq client, or None if GROQ_API_KEY is not set."""
    load_env()
    if not os.environ.get("GROQ_API_KEY"):
        return None
    return groq.Groq()


def describe_error(e):
    if isinstance(e, groq.AuthenticationError):
        return "The Groq API key was rejected."
    if isinstance(e, groq.RateLimitError):
        return "Rate limited - please wait a moment and try again."
    if isinstance(e, groq.APIStatusError):
        return f"API error {e.status_code}: {e.message}"
    if isinstance(e, groq.APIConnectionError):
        return "Could not reach the Groq API - check your connection."
    return "Something went wrong."

"""A simple terminal chatbot powered by Groq.

Usage:
    python chatbot.py

Commands:
    /reset  - clear the conversation history
    /quit   - exit (Ctrl+C or Ctrl+D also work)
"""

import sys

import groq

from llm import MODEL, describe_error, make_client

SYSTEM_PROMPT = "You are a friendly, helpful assistant. Keep answers clear and concise."


def main() -> None:
    client = make_client()
    if client is None:
        print("No API key found. Put GROQ_API_KEY=... in .env or set it as an environment variable.")
        sys.exit(1)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"Chatbot ready ({MODEL}). Type /reset to start over, /quit to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return

        if not user_input:
            continue
        if user_input == "/quit":
            print("Goodbye!")
            return
        if user_input == "/reset":
            del messages[1:]
            print("(conversation cleared)\n")
            continue

        messages.append({"role": "user", "content": user_input})

        print("Bot: ", end="", flush=True)
        reply = ""
        finish_reason = None
        try:
            stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True)
            for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.delta.content:
                    reply += choice.delta.content
                    print(choice.delta.content, end="", flush=True)
                finish_reason = choice.finish_reason or finish_reason
        except KeyboardInterrupt:
            print("\n(interrupted)\n")
            messages.pop()
            continue
        except groq.AuthenticationError as e:
            print(f"\n{describe_error(e)} Check GROQ_API_KEY.")
            sys.exit(1)
        except groq.APIError as e:
            print(f"\n{describe_error(e)}\n")
            messages.pop()
            continue

        print("\n")
        if finish_reason == "length":
            print("(response was cut off at the token limit)\n")

        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()

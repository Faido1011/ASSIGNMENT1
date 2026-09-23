"""
main.py
-------
DevMentor's entry point: startup, the interactive loop, conversation
history, and every call out to Ollama. This file is deliberately thin
on "policy" (what the assistant says or is called) - that lives in
config.py and prompts.py - and thick on "process" (reading input,
calling the API, handling failure, printing output).
"""

import json
import os
import sys
from datetime import datetime

import requests

import config
import prompts


# ----------------------------------------------------------------------
# Startup helpers
# ----------------------------------------------------------------------

def check_ollama_connection():
    """
    Ping Ollama's /api/tags endpoint. Returns the list of installed
    model names on success, or None if Ollama can't be reached.
    We check this ONCE at startup so the user gets one clear message
    instead of a cryptic failure on their first question.
    """
    try:
        response = requests.get(config.OLLAMA_TAGS_ENDPOINT, timeout=config.CONNECTION_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except requests.exceptions.RequestException:
        return None


def choose_model(installed_models):
    """
    Bonus 1: let the user pick a model at startup, from the models
    that are ACTUALLY installed (not just the suggested list), so we
    never let someone pick a model that will fail on first use.
    """
    if not installed_models:
        print(f"Could not list installed models. Falling back to '{config.DEFAULT_MODEL}'.")
        return config.DEFAULT_MODEL

    print("\nAvailable models:")
    for i, name in enumerate(installed_models, start=1):
        print(f"{i}. {name}")

    choice = input(f"Select model [1-{len(installed_models)}] (Enter for default): ").strip()

    if choice == "":
        # Prefer the configured default if it's actually installed.
        for name in installed_models:
            if name.startswith(config.DEFAULT_MODEL):
                return name
        return installed_models[0]

    if choice.isdigit() and 1 <= int(choice) <= len(installed_models):
        return installed_models[int(choice) - 1]

    print("Invalid choice. Using the first installed model instead.")
    return installed_models[0]


def choose_personality():
    """Bonus 5: let the user pick DevMentor's personality mode."""
    print("\nChoose a personality mode:")
    for key, (label, _) in config.PERSONALITY_MODES.items():
        print(f"{key}. {label}")

    choice = input(f"Select mode [Enter for default]: ").strip()
    if choice not in config.PERSONALITY_MODES:
        choice = config.DEFAULT_PERSONALITY

    label, prompt_name = config.PERSONALITY_MODES[choice]
    print(f"Personality set to: {label}\n")
    return prompts.get_personality_prompt(prompt_name)


# ----------------------------------------------------------------------
# Core chat mechanics
# ----------------------------------------------------------------------

def get_ai_response(messages, model):
    """
    Send the FULL message list to Ollama's chat endpoint and return the
    assistant's reply text.

    Why send the full list every time? Ollama's API is stateless - it
    has no memory of previous calls. Every request is judged only on
    what's inside THIS request's "messages" array. If we only sent the
    newest user message, the model would have no idea what "it" or
    "that" or "the second one" refers to. Conversation memory therefore
    isn't a feature of the API - it's a discipline in OUR code: we keep
    the list, and we resend it, every single turn.

    Raises requests.exceptions.RequestException on connection failure,
    which the caller handles so the user never sees a raw traceback.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(
        config.OLLAMA_CHAT_ENDPOINT,
        json=payload,
        timeout=config.CONNECTION_TIMEOUT * 6,  # generation can be slow
    )
    response.raise_for_status()
    data = response.json()

    if "message" not in data or "content" not in data.get("message", {}):
        raise ValueError("Ollama returned an unexpected response shape.")

    return data["message"]["content"]


def reset_conversation(messages, system_prompt):
    """
    Clear chat history but KEEP the system prompt. Returns a fresh
    messages list rather than mutating in place, so the caller decides
    what to do with the old one (useful for tests / clarity).
    """
    return [{"role": "system", "content": system_prompt}]


def display_history(messages):
    """
    Print the conversation so far as a numbered list of turns.
    The system prompt is deliberately skipped - it configures the
    assistant, it isn't something either party "said" in the chat.
    """
    turns = [m for m in messages if m["role"] != "system"]

    if not turns:
        print("(No conversation yet.)")
        return

    for i, msg in enumerate(turns, start=1):
        speaker = "USER" if msg["role"] == "user" else "ASSISTANT"
        print(f"{i}. {speaker}: {msg['content']}")


# ----------------------------------------------------------------------
# Bonus 2 / 3 - save and load conversations
# ----------------------------------------------------------------------

def save_conversation(messages):
    """Write the full message list (system prompt included) to disk."""
    os.makedirs(config.CONVERSATIONS_DIR, exist_ok=True)
    filename = f"chat_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}.json"
    path = os.path.join(config.CONVERSATIONS_DIR, filename)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2)
        print(f"Conversation saved to: {path}")
    except OSError as e:
        print(f"Could not save conversation: {e}")


def load_conversation(filename):
    """
    Load a previously saved message list. We restore the WHOLE list -
    system prompt, every user turn, every assistant turn - because
    that whole list IS the model's context. Restoring only the latest
    message would leave the model with no memory of anything earlier,
    exactly as if the chat had never happened.
    """
    path = filename if os.path.isabs(filename) else os.path.join(config.CONVERSATIONS_DIR, filename)

    try:
        with open(path, "r", encoding="utf-8") as f:
            messages = json.load(f)
        if not isinstance(messages, list) or not messages:
            raise ValueError("File does not contain a valid conversation.")
        print(f"Conversation loaded from: {path}")
        return messages
    except FileNotFoundError:
        print(f"No such file: {path}")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Could not load conversation: {e}")
        return None


# ----------------------------------------------------------------------
# Input handling
# ----------------------------------------------------------------------

def get_user_input():
    """Read one line from the user, tolerating Ctrl+C / Ctrl+D cleanly."""
    try:
        return input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        return "/exit"


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------

def main():
    print("=" * 40)
    print(f"{config.APP_NAME} AI Assistant - {config.APP_TAGLINE}")
    print("=" * 40)

    installed_models = check_ollama_connection()
    if installed_models is None:
        print("\nUnable to connect to Ollama.")
        print("Make sure Ollama is running and try again.")
        sys.exit(1)

    model = choose_model(installed_models)
    system_prompt = choose_personality()
    messages = [{"role": "system", "content": system_prompt}]

    print(f"Using model: {model}")
    print("Type your question, or use /reset, /history, /save, /load <file>, /exit.\n")

    while True:
        user_input = get_user_input()

        if user_input == "":
            print("Please type something - I can't send an empty message.")
            continue

        if user_input == "/exit":
            print("Goodbye!")
            break

        if user_input == "/reset":
            messages = reset_conversation(messages, system_prompt)
            print("Conversation reset.")
            continue

        if user_input == "/history":
            display_history(messages)
            continue

        if user_input == "/save":
            save_conversation(messages)
            continue

        if user_input.startswith("/load"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print("Usage: /load <filename>")
                continue
            loaded = load_conversation(parts[1].strip())
            if loaded is not None:
                messages = loaded
            continue

        # Ordinary chat turn: append the user's message, call the model,
        # append the reply. Both messages join the SAME list that gets
        # resent in full on the next turn - that list is the app's
        # entire memory of the conversation.
        messages.append({"role": "user", "content": user_input})

        try:
            reply = get_ai_response(messages, model)
        except requests.exceptions.ConnectionError:
            print("Unable to connect to Ollama. Make sure Ollama is running and try again.")
            messages.pop()  # don't keep a question that never got answered
            continue
        except requests.exceptions.Timeout:
            print("Ollama took too long to respond. Try again, or try a smaller model.")
            messages.pop()
            continue
        except requests.exceptions.HTTPError as e:
            print(f"Ollama rejected the request - check the model name is installed. ({e})")
            messages.pop()
            continue
        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"Something went wrong talking to Ollama: {e}")
            messages.pop()
            continue

        print(f"AI: {reply}\n")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()

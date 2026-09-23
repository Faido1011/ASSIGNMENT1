"""
config.py
---------
Central place for DevMentor's settings. Nothing in here talks to Ollama
directly - it just holds the values that main.py and prompts.py need.
Keeping this separate means changing a model name or a timeout never
requires touching the chat loop itself.
"""

# Basic app identity
APP_NAME = "DevMentor"
APP_TAGLINE = "Your local programming assistant"

# Where Ollama lives. Ollama's default local server is this address -
# nothing here talks to the internet.
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_ENDPOINT = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_ENDPOINT = f"{OLLAMA_BASE_URL}/api/tags"

# Model to use if the user doesn't pick one at startup (Bonus 1).
DEFAULT_MODEL = "llama3.2"

# Models we suggest at the model-selection prompt. This is just a
# suggestion list for the UI - the app still asks Ollama which models
# are ACTUALLY installed before trusting a choice.
SUGGESTED_MODELS = ["llama3.2", "qwen2.5", "mistral", "gemma"]

# How long we wait before deciding Ollama is unreachable, in seconds.
CONNECTION_TIMEOUT = 10

# Where saved chats go (Bonus 2 / 3).
CONVERSATIONS_DIR = "conversations"

# Personality modes (Bonus 5). Each key maps to a system prompt in
# prompts.py. This dict just defines the menu the user sees.
PERSONALITY_MODES = {
    "1": ("Beginner Tutor", "BEGINNER_TUTOR"),
    "2": ("Senior Engineer", "SENIOR_ENGINEER"),
    "3": ("Code Reviewer", "CODE_REVIEWER"),
    "4": ("Socratic Teacher", "SOCRATIC_TEACHER"),
}

# Which personality mode is active by default.
DEFAULT_PERSONALITY = "1"

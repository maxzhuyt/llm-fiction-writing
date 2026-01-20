"""
Configuration for Story Engine - models, default prompts, environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

# Available models for OpenRouter
AVAILABLE_MODELS = {
    # Anthropic
    "Claude Opus 4.5": "anthropic/claude-opus-4.5",
    "Claude Opus 4": "anthropic/claude-opus-4",
    "Claude Sonnet 4.5": "anthropic/claude-sonnet-4.5",
    "Claude Sonnet 4": "anthropic/claude-sonnet-4",
    "Claude 3.5 Sonnet": "anthropic/claude-3.5-sonnet",
    # OpenAI
    "GPT-4o": "openai/gpt-4o",
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "GPT-4 Turbo": "openai/gpt-4-turbo",
    "o1": "openai/o1",
    "o1 Mini": "openai/o1-mini",
    # Google
    "Gemini 2.0 Flash": "google/gemini-2.0-flash-001",
    "Gemini 1.5 Pro": "google/gemini-pro-1.5",
    "Gemini 1.5 Flash": "google/gemini-flash-1.5",
    # Mistral
    "Mistral Small Creative": "mistralai/mistral-small-creative",
    "Mistral Large": "mistralai/mistral-large",
    "Mistral Medium": "mistralai/mistral-medium",
}

# Default prompts for each step
DEFAULT_STEP0_SYSTEM = "You are a story structure analyst."
DEFAULT_STEP0_USER = "Create a 5-point to-do list of the most important structural beats for the story: The Ones Who Walk Away from Omelas"

DEFAULT_STEP1_SYSTEM = "Create a to-do list of the most important structural beats needed to tell this story."
DEFAULT_STEP1_USER = ""

DEFAULT_STEP2_SYSTEM = "Write a story based on the to-do list provided."
DEFAULT_STEP2_USER = ""

# Step metadata
STEPS = [
    {
        "num": 0,
        "title": "Template",
        "button_label": "Generate Template",
        "default_system": DEFAULT_STEP0_SYSTEM,
        "default_user": DEFAULT_STEP0_USER,
    },
    {
        "num": 1,
        "title": "To-Do List Generator",
        "button_label": "Generate To-Do List",
        "default_system": DEFAULT_STEP1_SYSTEM,
        "default_user": DEFAULT_STEP1_USER,
    },
    {
        "num": 2,
        "title": "Story Decoder",
        "button_label": "Generate Story",
        "default_system": DEFAULT_STEP2_SYSTEM,
        "default_user": DEFAULT_STEP2_USER,
    },
]

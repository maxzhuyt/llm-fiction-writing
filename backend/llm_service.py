"""
LLM Service for Story Engine - Async OpenRouter API client.
"""

from typing import List, Dict, Optional
from openai import AsyncOpenAI


def get_client(api_key: str) -> AsyncOpenAI:
    """Create an async OpenAI client configured for OpenRouter.

    Args:
        api_key: OpenRouter API key

    Returns:
        AsyncOpenAI client instance
    """
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


async def call_llm(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
    previous_context: Optional[List[Dict[str, str]]] = None
) -> str:
    """Make an async completion request to the LLM.

    Args:
        client: AsyncOpenAI client
        model: Model ID (e.g., "anthropic/claude-3.5-sonnet")
        system_prompt: System prompt for the conversation
        user_message: Current user message
        previous_context: List of previous step interactions, each containing
                         {'user': str, 'assistant': str}

    Returns:
        LLM response content or error message
    """
    try:
        messages = [{"role": "system", "content": system_prompt}]

        # Add previous context as conversation history
        if previous_context:
            for ctx in previous_context:
                if ctx.get('user'):
                    messages.append({"role": "user", "content": ctx['user']})
                if ctx.get('assistant'):
                    messages.append({"role": "assistant", "content": ctx['assistant']})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"

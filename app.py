"""
Story Engine - A two-stage fiction generation pipeline using Streamlit and OpenRouter.
"""

import streamlit as st
from openai import OpenAI
from datetime import datetime
from pathlib import Path

# =============================================================================
# Password Gate
# =============================================================================

def password_gate():
    if "APP_PASSWORD" not in st.sec1rets:
        return

    if "authed" not in st.session_state:
        st.session_state.authed = False

    if st.session_state.authed:
        return

    st.title("🔒 Protected App")
    pw = st.text_input("Enter password", type="password")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Login"):
            if pw == st.secrets["APP_PASSWORD"]:
                st.session_state.authed = True
                st.rerun()
            else:
                st.error("Wrong password")
    with c2:
        if st.button("Clear"):
            st.session_state.authed = False
            st.rerun()

    st.stop()

password_gate()

# =============================================================================
# Configuration
# =============================================================================

AVAILABLE_MODELS = {
    "Claude 3.5 Sonnet": "anthropic/claude-3.5-sonnet",
    "Claude 4.5 Sonnet": "anthropic/claude-4.5-sonnet",
    "Claude 3 Opus": "anthropic/claude-3-opus",
}

DEFAULT_TODO_PROMPT = "Create a 5-point to-do list of the most important structural beats needed to tell this story"

DEFAULT_STORY_PROMPT = "Write a 20-sentence story based on the to-do list."


# =============================================================================
# API Client
# =============================================================================

def get_client(api_key: str) -> OpenAI:
    """Create an OpenAI client configured for OpenRouter."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def call_llm(client: OpenAI, model: str, system_prompt: str, user_message: str) -> str:
    """Make a completion request to the LLM."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# Pipeline Stages
# =============================================================================

def generate_todo_list(client: OpenAI, model: str, system_prompt: str, user_query: str) -> str:
    """Stage 1: Generate a structured to-do list from user query."""
    return call_llm(client, model, system_prompt, user_query)


def generate_story(client: OpenAI, model: str, system_prompt: str, todo_list: str, user_guidance: str) -> str:
    """Stage 2: Expand to-do list into full story."""
    if user_guidance:
        combined_input = f"{todo_list}\n\n{user_guidance}"
    else:
        combined_input = todo_list
    return call_llm(client, model, system_prompt, combined_input)


# =============================================================================
# Persistence
# =============================================================================

def save_session(query: str, todo_prompt: str, story_prompt: str, todo_list: str, story: str) -> str:
    """Save the current session to a timestamped Markdown file."""
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = outputs_dir / f"story_session_{timestamp}.md"

    content = f"""# Story Engine Session
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Original Query
{query}

---

## To-Do List System Prompt
```
{todo_prompt}
```

## Story System Prompt
```
{story_prompt}
```

---

## Generated To-Do List
{todo_list}

---

## Final Story
{story}
"""

    filename.write_text(content)
    return str(filename)


# =============================================================================
# UI Components
# =============================================================================

def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.header("Configuration")

        # API Key
        st.subheader("API Key")
        api_key = st.text_input(
            "OpenRouter API Key",
            value="",
            type="password",
            placeholder="Enter your OpenRouter API key"
        )

        # Model Selection
        st.subheader("Model")
        model_name = st.selectbox(
            "Select Model",
            options=list(AVAILABLE_MODELS.keys()),
        )
        model_id = AVAILABLE_MODELS[model_name]

        return api_key, model_id


def render_main_interface(api_key: str, model_id: str):
    """Render the main interface with the two-stage pipeline."""

    # Initialize session state
    if "todo_list" not in st.session_state:
        st.session_state.todo_list = ""
    if "story" not in st.session_state:
        st.session_state.story = ""
    if "original_query" not in st.session_state:
        st.session_state.original_query = ""

    # Stage 1: To-Do List Generation
    st.header("Stage 1: To-Do List Generator")

    todo_prompt = st.text_area(
        "System Prompt",
        value=st.session_state.get("todo_prompt", DEFAULT_TODO_PROMPT),
        height=100,
        key="todo_prompt_input",
        placeholder="System prompt for to-do list generation..."
    )
    st.session_state.todo_prompt = todo_prompt

    user_query = st.text_area(
        "User Query",
        placeholder="Story idea, premise, characters, instructions for the model, or any other input...",
        height=100,
        key="user_query"
    )

    stage1_guidance = st.text_area(
        "Additional Guidance",
        placeholder="Extra instructions, constraints, formatting preferences...",
        height=100,
        key="stage1_guidance"
    )

    generate_todo_btn = st.button("Generate To-Do List", type="primary", disabled=not api_key)

    if generate_todo_btn and user_query:
        st.session_state.original_query = user_query
        with st.spinner("Generating To-Do List..."):
            client = get_client(api_key)
            # Combine user query and guidance if provided
            if stage1_guidance:
                combined_query = f"{user_query}\n\n{stage1_guidance}"
            else:
                combined_query = user_query
            result = generate_todo_list(client, model_id, todo_prompt, combined_query)
            st.session_state.todo_list = result
            # Force the edited field to sync by setting it in session state
            st.session_state.edited_todo_list = result
            st.rerun()

    st.divider()

    # Stage 2: Story Decoder
    st.header("Stage 2: Story Decoder")

    story_prompt = st.text_area(
        "System Prompt",
        value=st.session_state.get("story_prompt", DEFAULT_STORY_PROMPT),
        height=100,
        key="story_prompt_input",
        placeholder="System prompt for story generation..."
    )
    st.session_state.story_prompt = story_prompt

    # Initialize edited_todo_list from todo_list if not set
    if "edited_todo_list" not in st.session_state:
        st.session_state.edited_todo_list = st.session_state.todo_list

    edited_todo_list = st.text_area(
        "To-Do List (editable)",
        height=300,
        key="edited_todo_list",
        placeholder="Generated to-do list will appear here. You can also write or paste your own..."
    )

    story_guidance = st.text_area(
        "Additional Guidance",
        placeholder="Add style preferences, tone, POV, or other instructions...",
        height=100,
        key="story_guidance"
    )

    generate_story_btn = st.button("Generate Story", type="primary", disabled=not api_key)

    if generate_story_btn and edited_todo_list:
        with st.spinner("Generating Story..."):
            client = get_client(api_key)
            st.session_state.story = generate_story(
                client, model_id, story_prompt, edited_todo_list, story_guidance
            )

    # Display Story
    if st.session_state.story:
        st.divider()
        st.header("Generated Story")
        st.markdown(st.session_state.story)

        # Save Session
        st.divider()
        if st.button("Save Session"):
            filepath = save_session(
                st.session_state.original_query or user_query,
                todo_prompt,
                story_prompt,
                edited_todo_list,
                st.session_state.story
            )
            st.success(f"Session saved to: {filepath}")


# =============================================================================
# Main App
# =============================================================================

def main():
    st.set_page_config(
        page_title="Story Engine",
        page_icon="📖",
        layout="wide"
    )

    # Custom CSS for narrower sidebar (approximately 3:7 ratio)
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            min-width: 250px;
            max-width: 300px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Story Engine")
    st.caption("A two-stage fiction generation pipeline")

    api_key, model_id = render_sidebar()

    if not api_key:
        st.warning("Enter an OpenRouter API key in the sidebar to enable generation.")

    render_main_interface(api_key, model_id)


if __name__ == "__main__":
    main()

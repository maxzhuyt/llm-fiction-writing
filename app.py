"""
Story Engine - A fiction generation pipeline using Streamlit and OpenRouter.
"""

import streamlit as st
from openai import OpenAI
from datetime import datetime
from pathlib import Path

# =============================================================================
# Password Gate
# =============================================================================

def password_gate():
    if "APP_PASSWORD" not in st.secrets:
        return

    if "authed" not in st.session_state:
        st.session_state.authed = False

    if st.session_state.authed:
        return

    st.title("Protected App")
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

DEFAULT_STEP0_SYSTEM = "You are a story structure analyst."

DEFAULT_STEP0_USER = "Create a 5-point to-do list of the most important structural beats for the story: The Ones Who Walk Away from Omelas"

DEFAULT_STEP1_SYSTEM = "Create a to-do list of the most important structural beats needed to tell this story."

DEFAULT_STEP1_USER = ""

DEFAULT_STEP2_SYSTEM = "Write a story based on the to-do list provided."

DEFAULT_STEP2_USER = ""


# =============================================================================
# API Client
# =============================================================================

def get_client(api_key: str) -> OpenAI:
    """Create an OpenAI client configured for OpenRouter."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def call_llm(client: OpenAI, model: str, system_prompt: str, user_message: str,
              previous_context: list = None) -> str:
    """Make a completion request to the LLM.

    Args:
        previous_context: List of previous step interactions, each containing
                         {'system': str, 'user': str, 'assistant': str}
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

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# UI Components
# =============================================================================

def init_edit_state(key: str, default_value: str):
    """Initialize edit state for a text field."""
    if f"{key}_value" not in st.session_state:
        st.session_state[f"{key}_value"] = default_value
    if f"{key}_editing" not in st.session_state:
        st.session_state[f"{key}_editing"] = True


def render_editable_field(label: str, key: str, height: int = 100):
    """Render a text field with Edit/Done buttons."""
    editing = st.session_state.get(f"{key}_editing", False)

    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"**{label}**")
    with col2:
        if editing:
            if st.button("Done", key=f"{key}_done_btn", type="primary"):
                st.session_state[f"{key}_editing"] = False
                st.rerun()
        else:
            if st.button("Edit", key=f"{key}_edit_btn"):
                st.session_state[f"{key}_editing"] = True
                st.rerun()

    value = st.text_area(
        label,
        value=st.session_state.get(f"{key}_value", ""),
        height=height,
        key=f"{key}_input",
        disabled=not editing,
        label_visibility="collapsed"
    )

    if editing:
        st.session_state[f"{key}_value"] = value

    return st.session_state.get(f"{key}_value", "")


def export_prompt(step_num: int, system: str, user: str, step_title: str, include_previous: bool):
    """Generate export content for a step's prompts, optionally including previous steps."""
    lines = [f"Step {step_num}: {step_title} - Exported Prompts"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Include previous steps if enabled
    if include_previous and step_num > 0:
        lines.append("=" * 50)
        lines.append("PREVIOUS STEPS (included as context)")
        lines.append("=" * 50)
        lines.append("")

        for i in range(step_num):
            step_system = st.session_state.get(f"step{i}_system_value", "")
            step_user = st.session_state.get(f"step{i}_user_value", "")
            step_output = st.session_state.get(f"step{i}_output", "")

            lines.append(f"--- Step {i} ---")
            lines.append(f"System Prompt: {step_system}")
            lines.append("")
            lines.append(f"User Prompt: {step_user}")
            lines.append("")
            lines.append(f"Output: {step_output}")
            lines.append("")

        lines.append("=" * 50)
        lines.append("CURRENT STEP")
        lines.append("=" * 50)
        lines.append("")

    lines.append(f"System Prompt:")
    lines.append(system)
    lines.append("")
    lines.append(f"User Prompt:")
    lines.append(user)
    lines.append("")

    return "\n".join(lines)


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.header("Configuration")

        # API Key
        st.subheader("API Key")
        secret_api_key = st.secrets.get("OPENROUTER_API_KEY", "") if "OPENROUTER_API_KEY" in st.secrets else ""
        
        # If secret API key exists, show status and option to override
        if secret_api_key:
            st.success("✓ API Key configured")
            use_manual = st.checkbox("Override with manual input", key="override_api_key")
            
            if use_manual:
                manual_api_key = st.text_input(
                    "OpenRouter API Key",
                    value="",
                    type="password",
                    placeholder="Enter your OpenRouter API key",
                    key="manual_api_key_input"
                )
                api_key = manual_api_key if manual_api_key else secret_api_key
            else:
                api_key = secret_api_key
        else:
            # No secret API key, show normal input
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


def get_step_context(step_num: int) -> list:
    """Get the context from previous steps."""
    context = []
    for i in range(step_num):
        user_val = st.session_state.get(f"step{i}_user_value", "")
        output_val = st.session_state.get(f"step{i}_output", "")
        if user_val or output_val:
            context.append({
                'user': user_val,
                'assistant': output_val
            })
    return context


def render_step(step_num: int, step_title: str, system_key: str, user_key: str,
                default_system: str, default_user: str, api_key: str, model_id: str,
                output_key: str, button_label: str):
    """Render a single step with system/user prompts and generate button."""

    st.header(f"Step {step_num}: {step_title}")

    # Initialize states
    init_edit_state(system_key, default_system)
    init_edit_state(user_key, default_user)

    # System prompt
    system_prompt = render_editable_field("System Prompt", system_key, height=100)

    # User prompt
    user_prompt = render_editable_field("User Prompt", user_key, height=150)

    # Include previous steps checkbox (for steps 1 and 2)
    include_previous = False
    if step_num > 0:
        if step_num == 1:
            checkbox_label = "Build on Step 0"
            help_text = "Include Step 0's conversation as context"
        else:
            checkbox_label = "Build on previous steps"
            help_text = "Include all previous steps' conversations as context"
        include_previous = st.checkbox(checkbox_label, key=f"step{step_num}_include_prev", help=help_text)

    # Buttons row
    col1, col2 = st.columns([1, 1])
    with col1:
        generate_btn = st.button(button_label, type="primary", disabled=not api_key, key=f"step{step_num}_generate")
    with col2:
        export_content = export_prompt(step_num, system_prompt, user_prompt, step_title, include_previous)
        st.download_button(
            "Export Prompts",
            data=export_content,
            file_name=f"step{step_num}_prompts.txt",
            mime="text/plain",
            key=f"step{step_num}_export"
        )

    # Generate output
    if generate_btn and user_prompt:
        with st.spinner(f"Generating..."):
            client = get_client(api_key)
            # Get previous context if checkbox is enabled
            previous_context = get_step_context(step_num) if include_previous else None
            result = call_llm(client, model_id, system_prompt, user_prompt, previous_context)
            st.session_state[output_key] = result
            st.rerun()

    # Display output
    if st.session_state.get(output_key):
        st.markdown("**Output:**")
        if step_num == 2:
            # Step 2 (story) uses markdown for natural line breaks
            st.markdown(st.session_state[output_key])
            with st.expander("Copy text"):
                st.code(st.session_state[output_key], language=None)
        else:
            # Steps 0-1 use code block with built-in copy button
            st.code(st.session_state[output_key], language=None)

    return st.session_state.get(output_key, "")


def render_main_interface(api_key: str, model_id: str):
    """Render the main interface with the pipeline steps."""

    # Initialize output states
    if "step0_output" not in st.session_state:
        st.session_state.step0_output = ""
    if "step1_output" not in st.session_state:
        st.session_state.step1_output = ""
    if "step2_output" not in st.session_state:
        st.session_state.step2_output = ""

    # Step 0: Template
    render_step(
        step_num=0,
        step_title="Template",
        system_key="step0_system",
        user_key="step0_user",
        default_system=DEFAULT_STEP0_SYSTEM,
        default_user=DEFAULT_STEP0_USER,
        api_key=api_key,
        model_id=model_id,
        output_key="step0_output",
        button_label="Generate Template"
    )

    st.divider()

    # Step 1: To-Do List Generation
    render_step(
        step_num=1,
        step_title="To-Do List Generator",
        system_key="step1_system",
        user_key="step1_user",
        default_system=DEFAULT_STEP1_SYSTEM,
        default_user=DEFAULT_STEP1_USER,
        api_key=api_key,
        model_id=model_id,
        output_key="step1_output",
        button_label="Generate To-Do List"
    )

    st.divider()

    # Step 2: Story Decoder
    render_step(
        step_num=2,
        step_title="Story Decoder",
        system_key="step2_system",
        user_key="step2_user",
        default_system=DEFAULT_STEP2_SYSTEM,
        default_user=DEFAULT_STEP2_USER,
        api_key=api_key,
        model_id=model_id,
        output_key="step2_output",
        button_label="Generate Story"
    )

    # Save full session
    if st.session_state.get("step2_output"):
        st.divider()
        if st.button("Save Full Session"):
            filepath = save_session()
            st.success(f"Session saved to: {filepath}")


def save_session() -> str:
    """Save the current session to a timestamped Markdown file."""
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = outputs_dir / f"story_session_{timestamp}.md"

    content = f"""# Story Engine Session
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Step 0: Template Generation

### System Prompt
{st.session_state.get("step0_system_value", "")}

### User Prompt
{st.session_state.get("step0_user_value", "")}

### Output
{st.session_state.get("step0_output", "")}

---

## Step 1: To-Do List Generator

### System Prompt
{st.session_state.get("step1_system_value", "")}

### User Prompt
{st.session_state.get("step1_user_value", "")}

### Output
{st.session_state.get("step1_output", "")}

---

## Step 2: Story Decoder

### System Prompt
{st.session_state.get("step2_system_value", "")}

### User Prompt
{st.session_state.get("step2_user_value", "")}

### Output
{st.session_state.get("step2_output", "")}
"""

    filename.write_text(content)
    return str(filename)


# =============================================================================
# Main App
# =============================================================================

def main():
    st.set_page_config(
        page_title="Story Engine",
        page_icon="",
        layout="wide"
    )

    # Custom CSS for narrower sidebar
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

    api_key, model_id = render_sidebar()

    if not api_key:
        st.warning("Enter an OpenRouter API key in the sidebar to enable generation.")

    render_main_interface(api_key, model_id)


if __name__ == "__main__":
    main()

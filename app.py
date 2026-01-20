"""
Story Engine - A fiction generation pipeline using Streamlit and OpenRouter.
"""

import re
import streamlit as st
from openai import OpenAI
from datetime import datetime
from pathlib import Path
from st_copy_to_clipboard import st_copy_to_clipboard

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
# Variable Interpolation
# =============================================================================

def expand_variables(text: str) -> str:
    """Replace stepN_output placeholders with actual values."""
    pattern = r'\b(step\d+_output)\b'
    def replace_match(match):
        var_name = match.group(1)
        value = st.session_state.get(var_name, "")
        return value if value else f"[{var_name} not yet generated]"
    return re.sub(pattern, replace_match, text)


def get_detected_variables(text: str) -> list:
    """Return list of variable names found in the text."""
    pattern = r'\b(step\d+_output)\b'
    return list(set(re.findall(pattern, text)))


def has_variables(text: str) -> bool:
    """Check if text contains any variable placeholders."""
    pattern = r'\bstep\d+_output\b'
    return bool(re.search(pattern, text))


def get_available_variable_names(current_step: int) -> list:
    """Get list of available variable names based on generated outputs."""
    variables = []
    for i in range(current_step):
        if st.session_state.get(f"step{i}_output"):
            variables.append(f"step{i}_output")
    return variables


# =============================================================================
# UI Components
# =============================================================================

def init_edit_state(key: str, default_value: str):
    """Initialize edit state for a text field."""
    if f"{key}_value" not in st.session_state:
        st.session_state[f"{key}_value"] = default_value
    if f"{key}_editing" not in st.session_state:
        st.session_state[f"{key}_editing"] = True


def render_editable_field(label: str, key: str, height: int = 100,
                          step_num: int = None, allow_variables: bool = False):
    """Render a text field with Edit/Done buttons and copy button."""
    editing = st.session_state.get(f"{key}_editing", False)
    current_value = st.session_state.get(f"{key}_value", "")

    # Label
    st.markdown(f"**{label}**")

    # Main layout: text area on left, buttons on right
    text_col, btn_col = st.columns([6, 1])

    with text_col:
        if editing:
            # Use standard text area
            value = st.text_area(
                label,
                value=current_value,
                height=height,
                key=f"{key}_input",
                label_visibility="collapsed"
            )
            if value != current_value:
                st.session_state[f"{key}_value"] = value
                current_value = value
        else:
            # Display as styled text when not editing
            display_text = current_value if current_value else "(empty)"
            # Highlight variables in display mode
            if current_value and has_variables(current_value):
                highlighted = re.sub(
                    r'\b(step\d+_output)\b',
                    r'<span style="color: #16a34a; font-family: monospace; font-weight: bold; background: #dcfce7; padding: 2px 4px; border-radius: 3px;">\1</span>',
                    current_value
                )
                st.markdown(
                    f'<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; '
                    f'min-height: {height}px; white-space: pre-wrap; border: 1px solid #ddd;">{highlighted}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; '
                    f'min-height: {height}px; white-space: pre-wrap; border: 1px solid #ddd;">{display_text}</div>',
                    unsafe_allow_html=True
                )

    with btn_col:
        # Edit/Done button
        if editing:
            if st.button("Done", key=f"{key}_done_btn", type="primary", use_container_width=True):
                st.session_state[f"{key}_editing"] = False
                st.rerun()
        else:
            if st.button("Edit", key=f"{key}_edit_btn", use_container_width=True):
                st.session_state[f"{key}_editing"] = True
                st.rerun()

        # Copy button - copies to clipboard
        if current_value:
            st_copy_to_clipboard(current_value, key=f"{key}_copy")

    # Show detected variables below (for both editing and viewing)
    current_value = st.session_state.get(f"{key}_value", "")
    if has_variables(current_value):
        detected_vars = get_detected_variables(current_value)
        valid_vars = [v for v in detected_vars if st.session_state.get(v)]
        invalid_vars = [v for v in detected_vars if not st.session_state.get(v)]

        if valid_vars or invalid_vars:
            msg_parts = []
            if valid_vars:
                msg_parts.append(f"<span style='color: #16a34a;'>Ready: {', '.join(valid_vars)}</span>")
            if invalid_vars:
                msg_parts.append(f"<span style='color: #d97706;'>Pending: {', '.join(invalid_vars)}</span>")
            st.markdown(
                f"<div style='font-size: 12px; padding: 4px 8px; background: #f0f9ff; border-radius: 4px; margin-top: 4px;'>"
                f"Variables detected: {' | '.join(msg_parts)}</div>",
                unsafe_allow_html=True
            )

    return current_value


def export_prompt(step_num: int, system: str, user: str, step_title: str, include_previous: bool):
    """Generate export content for a step's prompts, optionally including previous steps.

    Note: Variables like step0_output are expanded to their actual values in the export.
    """
    # Expand variables in system and user prompts
    expanded_system = expand_variables(system)
    expanded_user = expand_variables(user)

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
            step_system = expand_variables(st.session_state.get(f"step{i}_system_value", ""))
            step_user = expand_variables(st.session_state.get(f"step{i}_user_value", ""))
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
    lines.append(expanded_system)
    lines.append("")
    lines.append(f"User Prompt:")
    lines.append(expanded_user)
    lines.append("")

    return "\n".join(lines)


def render_sidebar():
    """Render the sidebar with configuration options."""
    with st.sidebar:
        st.header("Configuration")

        # API Key
        st.subheader("API Key")

        # Try to get API key from secrets
        secret_api_key = ""
        secret_error = False
        try:
            if hasattr(st, 'secrets') and "OPENROUTER_API_KEY" in st.secrets:
                secret_api_key = st.secrets["OPENROUTER_API_KEY"]
        except Exception:
            secret_error = True

        # If secret API key exists, show prefilled with option to override
        if secret_api_key and not secret_error:
            st.success("API Key configured from environment")
            use_override = st.checkbox("Override API key", key="override_api_key")

            if use_override:
                api_key = st.text_input(
                    "OpenRouter API Key",
                    value="",
                    type="password",
                    placeholder="Enter a different API key",
                    key="manual_api_key_input"
                )
                # Fall back to secret if override is empty
                if not api_key:
                    api_key = secret_api_key
            else:
                api_key = secret_api_key
        else:
            # No secret API key or error reading secrets - show empty text input
            if secret_error:
                st.warning("Could not read API key from secrets")
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

    # System prompt (no variable support)
    system_prompt = render_editable_field("System Prompt", system_key, height=100)

    # User prompt (with variable support for steps 1 and 2)
    user_prompt = render_editable_field(
        "User Prompt", user_key, height=150,
        step_num=step_num, allow_variables=(step_num > 0)
    )

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
            # Expand variables in the user prompt before sending to LLM
            expanded_user_prompt = expand_variables(user_prompt)
            result = call_llm(client, model_id, system_prompt, expanded_user_prompt, previous_context)
            st.session_state[output_key] = result
            st.rerun()

    # Display output
    if st.session_state.get(output_key):
        output_text = st.session_state[output_key]
        st.markdown("**Output:**")

        if step_num == 2:
            # Step 2 (story) uses markdown for natural line breaks
            st.markdown(output_text)
            # Provide copy option via expander
            with st.expander("Copy text"):
                st.code(output_text, language=None)
        else:
            # Steps 0-1 use code block with built-in copy button
            st.code(output_text, language=None)

    return st.session_state.get(output_key, "")


def render_evaluation_panel(api_key: str, default_model_id: str):
    """Render the LLM evaluation panel at the bottom of the page."""
    # Initialize evaluation history
    if "evaluation_history" not in st.session_state:
        st.session_state.evaluation_history = []

    with st.expander("Evaluate Text with LLM", expanded=False):
        # Model selection for evaluation
        eval_model_name = st.selectbox(
            "Model for evaluation",
            options=list(AVAILABLE_MODELS.keys()),
            key="eval_model_select"
        )
        eval_model_id = AVAILABLE_MODELS[eval_model_name]

        text_to_evaluate = st.text_area(
            "Paste text to evaluate",
            height=100,
            key="eval_text_input",
            placeholder="Paste any text here that you want the LLM to evaluate..."
        )

        evaluation_prompt = st.text_input(
            "What would you like to know?",
            value="Analyze this text and provide feedback.",
            key="eval_prompt_input"
        )

        col1, col2 = st.columns([1, 1])
        with col1:
            evaluate_btn = st.button(
                "Evaluate",
                disabled=not text_to_evaluate or not api_key,
                key="eval_submit_btn",
                type="primary"
            )
        with col2:
            if st.button("Clear Conversation", key="eval_clear_btn"):
                st.session_state.evaluation_history = []
                st.rerun()

        # Handle evaluation
        if evaluate_btn and text_to_evaluate:
            with st.spinner("Evaluating..."):
                client = get_client(api_key)
                # Combine text and prompt for LLM
                combined_prompt = f"Text to evaluate:\n\n{text_to_evaluate}\n\nQuestion/Task: {evaluation_prompt}"
                result = call_llm(
                    client,
                    eval_model_id,
                    "You are a helpful assistant that evaluates and analyzes text.",
                    combined_prompt
                )
                # Add to history with model info
                st.session_state.evaluation_history.append({
                    'text': text_to_evaluate,
                    'prompt': evaluation_prompt,
                    'response': result,
                    'model': eval_model_name
                })
                st.rerun()

        # Display conversation history (most recent first)
        if st.session_state.evaluation_history:
            st.markdown("---")
            st.markdown("**Evaluation History:**")
            for i, item in enumerate(reversed(st.session_state.evaluation_history)):
                idx = len(st.session_state.evaluation_history) - i
                with st.container():
                    # Show truncated text and model used
                    text_preview = item['text'][:150] + "..." if len(item['text']) > 150 else item['text']
                    model_used = item.get('model', 'Unknown')
                    st.info(f"**#{idx}** ({model_used}) - **Text:** {text_preview}")
                    st.markdown(f"**Question:** {item['prompt']}")

                    # Response with copy via code block
                    st.markdown(f"**Response:**")
                    st.code(item['response'], language=None)
                    st.divider()


def render_main_interface(api_key: str, model_id: str):
    """Render the main interface with the pipeline steps."""

    # Initialize output states
    if "step0_output" not in st.session_state:
        st.session_state.step0_output = ""
    if "step1_output" not in st.session_state:
        st.session_state.step1_output = ""
    if "step2_output" not in st.session_state:
        st.session_state.step2_output = ""

    # Instructions for variable interpolation
    with st.expander("How to use variables", expanded=False):
        st.markdown("""
**Reference previous outputs in your prompts:**

Type `step0_output`, `step1_output`, etc. directly in any User Prompt field to reference the output from that step.

For example, in Step 1's User Prompt, you could write:
> Analyze the following template and create a detailed outline: step0_output

The system will automatically replace `step0_output` with the actual generated content when sending to the LLM.
        """)

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

    # Evaluation panel at the bottom
    st.divider()
    render_evaluation_panel(api_key, model_id)


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

    # Custom CSS and JavaScript for autocomplete
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            min-width: 250px;
            max-width: 300px;
        }

        /* Autocomplete popup styles */
        #step-autocomplete {
            position: fixed;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10000;
            display: none;
            max-width: 200px;
        }
        #step-autocomplete .autocomplete-item {
            padding: 8px 12px;
            cursor: pointer;
            font-family: monospace;
            font-size: 14px;
            color: #16a34a;
            background: #f8fff8;
        }
        #step-autocomplete .autocomplete-item:hover,
        #step-autocomplete .autocomplete-item.selected {
            background: #dcfce7;
        }
        #step-autocomplete .autocomplete-header {
            padding: 6px 12px;
            font-size: 11px;
            color: #666;
            background: #f0f0f0;
            border-bottom: 1px solid #ddd;
        }
        </style>

        <div id="step-autocomplete">
            <div class="autocomplete-header">Insert variable</div>
        </div>

        <script>
        (function() {
            // Prevent duplicate initialization
            if (window.stepAutocompleteInitialized) return;
            window.stepAutocompleteInitialized = true;

            const popup = document.getElementById('step-autocomplete');
            let activeTextarea = null;
            let selectedIndex = 0;
            let currentMatches = [];

            // All possible variables
            const allVariables = ['step0_output', 'step1_output', 'step2_output'];

            function getCaretCoordinates(element) {
                // Get approximate position for popup
                const rect = element.getBoundingClientRect();
                const style = getComputedStyle(element);
                const lineHeight = parseInt(style.lineHeight) || 20;
                const paddingTop = parseInt(style.paddingTop) || 0;
                const paddingLeft = parseInt(style.paddingLeft) || 0;

                // Simple approximation: place near top-left of textarea
                return {
                    top: rect.top + paddingTop + lineHeight,
                    left: rect.left + paddingLeft + 50
                };
            }

            function getCurrentWord(textarea) {
                const pos = textarea.selectionStart;
                const text = textarea.value;

                // Find word start
                let start = pos;
                while (start > 0 && /\w/.test(text[start - 1])) {
                    start--;
                }

                return {
                    word: text.substring(start, pos),
                    start: start,
                    end: pos
                };
            }

            function showPopup(textarea, matches) {
                if (matches.length === 0) {
                    hidePopup();
                    return;
                }

                currentMatches = matches;
                selectedIndex = 0;
                activeTextarea = textarea;

                // Build popup content
                let html = '<div class="autocomplete-header">Insert variable</div>';
                matches.forEach((m, i) => {
                    const cls = i === 0 ? 'autocomplete-item selected' : 'autocomplete-item';
                    html += '<div class="' + cls + '" data-value="' + m + '">' + m + '</div>';
                });
                popup.innerHTML = html;

                // Position popup
                const coords = getCaretCoordinates(textarea);
                popup.style.top = coords.top + 'px';
                popup.style.left = coords.left + 'px';
                popup.style.display = 'block';

                // Add click handlers
                popup.querySelectorAll('.autocomplete-item').forEach(item => {
                    item.addEventListener('click', function() {
                        insertVariable(this.dataset.value);
                    });
                });
            }

            function hidePopup() {
                popup.style.display = 'none';
                activeTextarea = null;
                currentMatches = [];
            }

            function updateSelection() {
                const items = popup.querySelectorAll('.autocomplete-item');
                items.forEach((item, i) => {
                    item.classList.toggle('selected', i === selectedIndex);
                });
            }

            function insertVariable(varName) {
                if (!activeTextarea) return;

                const wordInfo = getCurrentWord(activeTextarea);
                const before = activeTextarea.value.substring(0, wordInfo.start);
                const after = activeTextarea.value.substring(wordInfo.end);

                activeTextarea.value = before + varName + after;

                // Set cursor position after inserted text
                const newPos = wordInfo.start + varName.length;
                activeTextarea.setSelectionRange(newPos, newPos);

                // Trigger input event for Streamlit to pick up the change
                activeTextarea.dispatchEvent(new Event('input', { bubbles: true }));

                hidePopup();
                activeTextarea.focus();
            }

            // Monitor for textarea input
            document.addEventListener('input', function(e) {
                if (e.target.tagName !== 'TEXTAREA') return;

                const wordInfo = getCurrentWord(e.target);
                const word = wordInfo.word.toLowerCase();

                // Check if typing something that starts with "step"
                if (word.startsWith('step') && word.length >= 4) {
                    // Filter variables that match
                    const matches = allVariables.filter(v =>
                        v.toLowerCase().startsWith(word) && v.toLowerCase() !== word
                    );
                    showPopup(e.target, matches);
                } else {
                    hidePopup();
                }
            }, true);

            // Handle keyboard navigation
            document.addEventListener('keydown', function(e) {
                if (popup.style.display !== 'block') return;

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, currentMatches.length - 1);
                    updateSelection();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, 0);
                    updateSelection();
                } else if (e.key === 'Enter' || e.key === 'Tab') {
                    if (currentMatches.length > 0) {
                        e.preventDefault();
                        insertVariable(currentMatches[selectedIndex]);
                    }
                } else if (e.key === 'Escape') {
                    hidePopup();
                }
            }, true);

            // Hide popup when clicking outside
            document.addEventListener('click', function(e) {
                if (!popup.contains(e.target) && e.target !== activeTextarea) {
                    hidePopup();
                }
            });

            // Hide popup on scroll
            document.addEventListener('scroll', hidePopup, true);
        })();
        </script>
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

# Story Engine

A multi-stage fiction generation pipeline using LLMs via OpenRouter. Built with a FastAPI backend and vanilla JS frontend.

## Quick Start

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key-here"   # optional, can also enter in UI
uvicorn backend.main:app --reload
```

Opens at `http://localhost:8000`. Enter your OpenRouter API key in the sidebar (or set it via environment variable).

## How It Works

The pipeline has three sequential stages. Each stage sends a system prompt and user prompt to the LLM and produces an output. Later stages can reference earlier outputs via variable interpolation.

**Step 0: Template Generator**
- Generates a story structure/framework (e.g. structural beats for a reference story)
- Produces `step0_output`

**Step 1: To-Do List Generator**
- Generates detailed structural beats for the new story
- Can reference `step0_output` in its user prompt
- Produces `step1_output`

**Step 2: Story Decoder**
- Generates the full story text
- Can reference `step0_output` and `step1_output` in its user prompt
- Produces `step2_output`

Each step also has a "Build on previous steps" checkbox that includes the full conversation history from earlier steps as context (injected as prior user/assistant message pairs).

### Variable Interpolation

User prompts can contain `step0_output`, `step1_output`, or `step2_output` as plain text. These placeholders are expanded server-side to the actual generated text before being sent to the LLM. The UI highlights variables and shows their status (Ready vs Pending). Autocomplete is available in the CodeMirror editors.

### Evaluation Panel

A collapsible panel at the bottom of the UI lets you evaluate generated stories using an LLM. It has its own model selector and prompt editors, and can reference any step output via the same variable system. Evaluation history is persisted in localStorage.

### Design Philosophy

All inputs to the LLM are visible in the interface. No hidden prompts.

## Project Structure

```
├── backend/
│   ├── main.py               # FastAPI routes and Pydantic request models
│   ├── config.py              # Models, default prompts, env vars, step metadata
│   ├── llm_service.py         # Async OpenRouter client (OpenAI-compatible)
│   └── variable_service.py    # Variable detection, expansion, and validation
│
├── frontend/
│   ├── templates/
│   │   └── index.html         # Jinja2 template served by FastAPI
│   └── static/
│       ├── css/main.css
│       └── js/
│           ├── app.js         # Main application logic, API calls, state management
│           └── editor.js      # CodeMirror setup with custom variable highlighting
│
├── generate_story_ideas.py    # Standalone batch story idea generator
├── genres.py                  # 150+ pre-1970 genre definitions, 70+ document types
├── app.py                     # Legacy Streamlit app (kept for reference, not used)
├── requirements.txt
├── Procfile                   # Railway deployment
└── generated_ideas/           # Output from generate_story_ideas.py
```

## Backend

### API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Serve the main HTML page |
| `/api/models` | GET | Return available models |
| `/api/config` | GET | Return app configuration (models, steps, env flags) |
| `/api/check-password` | POST | Verify optional app password |
| `/api/generate` | POST | Generate output for a pipeline step |
| `/api/evaluate` | POST | Evaluate text using an LLM |
| `/api/export` | POST | Export prompts as plain text |
| `/api/save-session` | POST | Save full session to markdown in `outputs/` |
| `/api/validate-variables` | POST | Validate variable placeholders in text |

### Key Request Models

**`GenerateRequest`** — used by `/api/generate`:
- `api_key`, `model_id`, `system_prompt`, `user_prompt`
- `outputs: Dict[str, str]` — map of variable names to values (e.g. `{"step0_output": "..."}`)
- `include_previous: bool` — whether to include prior steps as conversation history
- `step_num: int` — current step index

**`EvaluateRequest`** — used by `/api/evaluate`:
- Same as GenerateRequest but without `include_previous` or `step_num`

### LLM Service (`backend/llm_service.py`)

Uses `openai.AsyncOpenAI` pointed at `https://openrouter.ai/api/v1`. Messages are built as:
1. System message from the system prompt
2. (Optional) Previous step user/assistant pairs if "Build on previous steps" is enabled
3. Current user message (with variables already expanded)

### Variable Service (`backend/variable_service.py`)

- `expand_variables(text, outputs)` — regex-replaces `stepN_output` with actual values
- `get_detected_variables(text)` — returns list of variable names found
- `validate_variables(text, outputs)` — categorizes variables as `valid` or `pending`

### Configuration (`backend/config.py`)

- **Models**: Anthropic (Claude 3.5 Sonnet through Opus 4.5), OpenAI (GPT-4o, o1), Google (Gemini), Mistral
- **Default prompts**: Defined as `DEFAULT_STEP{N}_SYSTEM` and `DEFAULT_STEP{N}_USER`
- **Step metadata**: `STEPS` list defines each step's number, title, button label, and defaults
- **Env vars**: `OPENROUTER_API_KEY` (API key), `APP_PASSWORD` (optional password gate)

## Frontend

Vanilla JavaScript with CodeMirror 5 editors. No build step or framework.

- **State**: All prompts, outputs, model selection, and evaluation history persisted in `localStorage`. API keys are NOT stored.
- **Variable highlighting**: Custom CodeMirror mode (`story-variables`) highlights `stepN_output` tokens with colored badges showing Ready/Pending status.
- **Autocomplete**: Triggered by typing "step" + Ctrl-Space or Tab.
- **Edit/Done toggle**: Editors can be locked to read-only after generation.
- **Session export**: "Save Full Session" writes a markdown file to `outputs/` via the backend.

## Story Idea Generator

`generate_story_ideas.py` is a standalone script that batch-generates story ideas (default 50).

**Process:**
1. Builds a vocabulary of ~10k+ real English words from the tokenizer (tiktoken `cl100k_base`) filtered against NLTK's dictionary
2. For each idea: re-primes with 5 random pre-1970 literary genres (asks the LLM to recall famous stories and extract narrative techniques), then samples 20 random words and asks the LLM to generate a story idea using at least 5 of them, with a specific narrative form (letter, transcript, memo, etc.)

**Configuration** (constants at top of file): `NUM_IDEAS` (default 50), `REPRIME_EVERY` (default 1 — re-primes every idea), `MODEL`, `MAX_TOKEN_ID`.

**API key**: Reads from a `credential` file in the repo root (not `.env`).

**Output:** `generated_ideas/batch_YYYYMMDD_HHMMSS/` containing individual idea files, a combined `all_ideas.md`, and `metadata.json`.

**Extra dependencies** (not in requirements.txt): `tiktoken`, `nltk`

## Adding a New Step

1. Add default prompts in `backend/config.py` (`DEFAULT_STEP{N}_SYSTEM`, `DEFAULT_STEP{N}_USER`)
2. Add an entry to the `STEPS` list in `backend/config.py`
3. The frontend auto-renders steps from the Jinja2 template loop — no frontend changes needed

## Adding a New Model

Add an entry to `AVAILABLE_MODELS` in `backend/config.py`:
```python
"Display Name": "provider/model-id",
```

No other changes needed. All models use OpenRouter's unified API.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | No | Pre-configured API key (users can also enter one in the UI) |
| `APP_PASSWORD` | No | Password-protect the app |

Both can be set in a `.env` file (loaded via `python-dotenv`).

## Deployment

**Railway** (via Procfile):
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Dev Container**: Python 3.11, configured in `.devcontainer/devcontainer.json` (still references legacy Streamlit setup).

## Requirements

- Python 3.8+
- OpenRouter API key ([openrouter.ai](https://openrouter.ai))

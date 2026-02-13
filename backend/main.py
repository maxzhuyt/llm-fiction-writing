"""
Story Engine - FastAPI Backend
Main application with routes for LLM generation, export, and session management.
"""

import random
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .config import (
    AVAILABLE_MODELS,
    OPENROUTER_API_KEY,
    APP_PASSWORD,
    STEPS,
    IDEA_STEPS,
    ALL_GENRES,
)
from .llm_service import get_client, call_llm
from .variable_service import expand_variables, validate_variables
from . import s3_service
from . import vocab_service

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Story Engine")

# Get the base directory (parent of backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static"
)

# Setup Jinja2 templates
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")


# Pre-warm vocabulary in a background thread at startup
@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=vocab_service.warm_up, daemon=True)
    thread.start()
    logger.info("Vocabulary warm-up started in background thread")


# Pydantic models for request/response
class GenerateRequest(BaseModel):
    api_key: str
    model_id: str
    system_prompt: str
    user_prompt: str
    outputs: Dict[str, str] = {}
    include_previous: bool = False
    step_num: int = 0


class IdeaGenerateRequest(BaseModel):
    api_key: str
    model_id: str
    system_prompt: str
    user_prompt: str
    outputs: Dict[str, str] = {}
    step_num: int = 0
    include_priming: bool = True


class EvaluateRequest(BaseModel):
    api_key: str
    model_id: str
    system_prompt: str
    user_prompt: str
    outputs: Dict[str, str] = {}


class ExportRequest(BaseModel):
    step_num: int
    step_title: str
    system_prompt: str
    user_prompt: str
    outputs: Dict[str, str] = {}
    include_previous: bool = False
    all_prompts: Optional[List[Dict]] = None


class SaveSessionRequest(BaseModel):
    steps: List[Dict]


class PasswordCheckRequest(BaseModel):
    password: str


# ─── Page Routes ───

@app.get("/")
async def index(request: Request):
    """Serve the main story page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "models": AVAILABLE_MODELS,
            "steps": STEPS,
            "has_env_api_key": bool(OPENROUTER_API_KEY),
            "has_password": bool(APP_PASSWORD),
        }
    )


@app.get("/ideas")
async def ideas_page(request: Request):
    """Serve the idea generator page."""
    return templates.TemplateResponse(
        "ideas.html",
        {
            "request": request,
            "models": AVAILABLE_MODELS,
            "idea_steps": IDEA_STEPS,
            "has_env_api_key": bool(OPENROUTER_API_KEY),
            "has_password": bool(APP_PASSWORD),
        }
    )


# ─── Shared API Routes ───

@app.get("/api/models")
async def get_models():
    """Return available models."""
    return {"models": AVAILABLE_MODELS}


@app.get("/api/config")
async def get_config():
    """Return configuration for the frontend."""
    return {
        "models": AVAILABLE_MODELS,
        "steps": STEPS,
        "has_env_api_key": bool(OPENROUTER_API_KEY),
        "has_password": bool(APP_PASSWORD),
    }


@app.post("/api/check-password")
async def check_password(req: PasswordCheckRequest):
    """Check if password is correct."""
    if not APP_PASSWORD:
        return {"valid": True}
    return {"valid": req.password == APP_PASSWORD}


# ─── Story Generation Routes ───

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Generate LLM output for a story step."""
    # Use provided API key or fall back to environment variable
    api_key = req.api_key or OPENROUTER_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    # Expand variables in the user prompt
    expanded_user_prompt = expand_variables(req.user_prompt, req.outputs)

    # Build previous context if needed
    previous_context = None
    if req.include_previous and req.step_num > 0:
        previous_context = []
        for i in range(req.step_num):
            user_val = req.outputs.get(f"step{i}_user", "")
            output_val = req.outputs.get(f"step{i}_output", "")
            if user_val or output_val:
                previous_context.append({
                    'user': user_val,
                    'assistant': output_val
                })

    # Call LLM
    client = get_client(api_key)
    result = await call_llm(
        client,
        req.model_id,
        req.system_prompt,
        expanded_user_prompt,
        previous_context
    )

    # Record to S3
    await s3_service.record_session(
        page="story",
        action="generate",
        step_info={"step_num": req.step_num, "system_prompt": req.system_prompt, "user_prompt": req.user_prompt},
        model_id=req.model_id,
        outputs={**req.outputs, f"step{req.step_num}_output": result},
    )

    return {"output": result}


@app.post("/api/evaluate")
async def evaluate(req: EvaluateRequest):
    """Evaluate text with LLM."""
    # Use provided API key or fall back to environment variable
    api_key = req.api_key or OPENROUTER_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    # Expand variables in the user prompt
    expanded_user_prompt = expand_variables(req.user_prompt, req.outputs)

    client = get_client(api_key)
    result = await call_llm(
        client,
        req.model_id,
        req.system_prompt,
        expanded_user_prompt
    )

    # Record to S3
    await s3_service.record_session(
        page="story",
        action="evaluate",
        step_info={"system_prompt": req.system_prompt, "user_prompt": req.user_prompt},
        model_id=req.model_id,
        outputs=req.outputs,
    )

    return {"response": result}


@app.post("/api/export", response_class=PlainTextResponse)
async def export_prompts(req: ExportRequest):
    """Export prompts to text format (variables kept as-is, not expanded)."""
    lines = [f"Step {req.step_num}: {req.step_title} - Exported Prompts"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Include previous steps if enabled
    if req.include_previous and req.step_num > 0 and req.all_prompts:
        lines.append("=" * 50)
        lines.append("PREVIOUS STEPS (included as context)")
        lines.append("=" * 50)
        lines.append("")

        for i in range(req.step_num):
            step_data = req.all_prompts[i] if i < len(req.all_prompts) else {}
            step_system = step_data.get("system", "")
            step_user = step_data.get("user", "")
            step_output = req.outputs.get(f"step{i}_output", "")

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

    lines.append("System Prompt:")
    lines.append(req.system_prompt)
    lines.append("")
    lines.append("User Prompt:")
    lines.append(req.user_prompt)
    lines.append("")

    return "\n".join(lines)


@app.post("/api/save-session")
async def save_session(req: SaveSessionRequest):
    """Save the current session to a markdown file."""
    outputs_dir = BASE_DIR / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = outputs_dir / f"story_session_{timestamp}.md"

    content = f"""# Story Engine Session
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""

    for step in req.steps:
        content += f"""## Step {step.get('num', 0)}: {step.get('title', 'Unknown')}

### System Prompt
{step.get('system', '')}

### User Prompt
{step.get('user', '')}

### Output
{step.get('output', '')}

---

"""

    filename.write_text(content)
    return {"filepath": str(filename), "filename": filename.name}


@app.post("/api/validate-variables")
async def validate_vars(outputs: Dict[str, str], text: str):
    """Validate variables in text."""
    result = validate_variables(text, outputs)
    return result


# ─── Idea Generation Routes ───

@app.post("/api/ideas/sample-genres")
async def sample_genres():
    """Sample random genres and generate a priming prompt."""
    sampled = random.sample(ALL_GENRES, 5)
    start_year = random.randrange(1910, 1971, 10)
    end_year = start_year + 50
    time_period = f"{start_year}-{end_year}"

    genre_list = "\n".join(f"- {genre}" for genre in sampled)

    prompt = f"""Let's warm up your creative circuits. Here are 5 randomly selected literary genres:
{genre_list}

For each genre, recall ONE famous story (published roughly around {time_period}) that exemplifies it.
For each story, explain in 1-2 sentences what narrative technique or structural choice made it memorable.
Focus on specific craft elements: how did the author create tension, develop character, and subvert expectations? What makes the ending particularly memorable or surprising?"""

    return {"prompt": prompt, "genres": sampled, "time_period": time_period}


@app.post("/api/ideas/sample-words")
async def sample_words():
    """Sample random words from vocabulary and generate an idea prompt."""
    words = vocab_service.sample_words(20)
    word_list = ", ".join(words)

    prompt = f"""Here are 20 randomly selected words:

{word_list}

Using at least 5 of these words as inspiration (not necessarily literally), generate a compelling story idea (3-4 sentences).
Before you generate, think about:
What is the core situation? What makes this story impossible to put down?
What is the form that this story should take? (such as personal letter, journal, interview transcript, bureaucratic report, diplomatic correspondence, research log, notebook, company memo, obituary, field notes, pamphlet, ad, telegram, etc.)
Your response should include the story idea only. No intro, no outro. Be specific. Avoid generic tropes."""

    return {"prompt": prompt, "words": words}


@app.post("/api/ideas/generate")
async def generate_idea(req: IdeaGenerateRequest):
    """Generate LLM output for an idea step."""
    api_key = req.api_key or OPENROUTER_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    # Expand variables in the user prompt
    expanded_user_prompt = expand_variables(req.user_prompt, req.outputs)

    # Build context based on step
    previous_context = None
    if req.step_num == 1 and req.include_priming:
        # For idea generation step, include priming output as assistant message
        # This matches the pattern from generate_story_ideas.py
        priming_output = req.outputs.get("priming_output", "")
        if priming_output:
            previous_context = [{"assistant": priming_output}]
    elif req.step_num == 2:
        # For post-processing, include full context chain
        context_parts = []
        priming = req.outputs.get("priming_output", "")
        if priming:
            context_parts.append({"assistant": priming})
        idea_user = req.outputs.get("idea_step1_user", "")
        idea_output = req.outputs.get("idea_output", "")
        if idea_user or idea_output:
            context_parts.append({"user": idea_user, "assistant": idea_output})
        if context_parts:
            previous_context = context_parts

    client = get_client(api_key)
    result = await call_llm(
        client,
        req.model_id,
        req.system_prompt,
        expanded_user_prompt,
        previous_context
    )

    # Record to S3
    output_var = IDEA_STEPS[req.step_num]["output_var"] if req.step_num < len(IDEA_STEPS) else f"step{req.step_num}_output"
    await s3_service.record_session(
        page="ideas",
        action="generate",
        step_info={"step_num": req.step_num, "system_prompt": req.system_prompt, "user_prompt": req.user_prompt},
        model_id=req.model_id,
        outputs={**req.outputs, output_var: result},
    )

    return {"output": result}


# Create __init__.py for backend package
init_file = Path(__file__).parent / "__init__.py"
if not init_file.exists():
    init_file.write_text("")

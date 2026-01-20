"""
Story Engine - FastAPI Backend
Main application with routes for LLM generation, export, and session management.
"""

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
)
from .llm_service import get_client, call_llm
from .variable_service import expand_variables, validate_variables

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


# Pydantic models for request/response
class GenerateRequest(BaseModel):
    api_key: str
    model_id: str
    system_prompt: str
    user_prompt: str
    outputs: Dict[str, str] = {}
    include_previous: bool = False
    step_num: int = 0


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


# Routes
@app.get("/")
async def index(request: Request):
    """Serve the main page."""
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


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Generate LLM output for a step."""
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


# Create __init__.py for backend package
init_file = Path(__file__).parent / "__init__.py"
if not init_file.exists():
    init_file.write_text("")

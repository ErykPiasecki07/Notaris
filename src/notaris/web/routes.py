"""HTTP routes for the Notaris web app."""

from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from notaris.domain.parsing import parse_csv_batch, parse_text_batch

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the homepage."""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report application health for local checks and tests."""
    return {"status": "ok"}


@router.get("/notes/batch", response_class=HTMLResponse)
async def batch_input_form(request: Request):
    """Render the batch note input form."""
    return templates.TemplateResponse(
        request=request, name="batch_input.html", context={}
    )


@router.post("/notes/batch", response_class=HTMLResponse)
async def process_batch_input(
    request: Request,
    pasted_notes: Annotated[Optional[str], Form()] = None,
    upload_file: Optional[UploadFile] = None,
):
    """Process pasted notes or uploaded files containing notes."""
    errors = []
    notes = []

    file_content = ""
    # Process uploaded file first, if provided and not empty
    if upload_file and upload_file.filename:
        try:
            content_bytes = await upload_file.read()
            file_content = content_bytes.decode("utf-8")
        except Exception:
            errors.append("Failed to read the uploaded file.")

    # Decide which input to use: File takes precedence if both provided
    if file_content.strip():
        if upload_file.filename and upload_file.filename.endswith(".csv"):
            try:
                notes = parse_csv_batch(file_content)
            except Exception:
                errors.append("Failed to parse CSV file.")
        else:
            notes = parse_text_batch(file_content)
    elif pasted_notes and pasted_notes.strip():
        notes = parse_text_batch(pasted_notes)
    else:
        errors.append("Please provide notes either by pasting or uploading a file.")

    if not errors and not notes:
        errors.append("No valid notes found in the input.")

    if errors:
        return templates.TemplateResponse(
            request=request, name="batch_input.html", context={"errors": errors}
        )

    return templates.TemplateResponse(
        request=request, name="batch_input_review.html", context={"notes": notes}
    )

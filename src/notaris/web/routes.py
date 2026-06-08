"""HTTP routes for the Notaris web app."""

import json
import os
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from notaris.domain.models import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.domain.parsing import parse_csv_batch, parse_text_batch
from notaris.providers import (
    PROVIDER_LABELS,
    ProviderConfigError,
    ProviderKind,
    build_provider,
    provider_config_from_form,
    provider_config_from_session,
)
from notaris.services.export import export_results_to_csv
from notaris.services.extraction import BatchExtractionService

router = APIRouter()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _provider_template_context(request: Request) -> dict[str, Any]:
    """Shared template context for provider selection UI."""
    session_config = request.session.get("provider_config")
    provider_config = provider_config_from_session(session_config)
    return {
        "provider_config": provider_config,
        "provider_options": [
            (kind.value, PROVIDER_LABELS[kind]) for kind in ProviderKind
        ],
        "google_api_key_configured": bool(os.getenv("GOOGLE_API_KEY")),
    }


def _save_provider_config(request: Request, **form_values: str | None) -> None:
    """Persist provider settings for the current demo session."""
    config = provider_config_from_form(**form_values)
    request.session["provider_config"] = config.model_dump()


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

    # Persist parsed notes in session for downstream extraction
    request.session["notes"] = [note.model_dump() for note in notes]

    return templates.TemplateResponse(
        request=request, name="batch_input_review.html", context={"notes": notes}
    )


@router.get("/schema/new", response_class=HTMLResponse)
async def schema_builder(request: Request):
    """Render the schema builder form."""
    schema_dump = request.session.get("schema", {})
    return templates.TemplateResponse(
        request=request, name="schema_builder.html", context={"schema": schema_dump}
    )


@router.post("/schema/new", response_class=HTMLResponse)
async def save_schema(
    request: Request,
    schema_data: Annotated[str, Form()],
):
    """Process and validate a new extraction schema."""
    try:
        data = json.loads(schema_data)
        # Parse into a list of dictionaries if it's not
        if not isinstance(data, list):
            raise ValueError("Schema fields must be a list of field definitions.")

        # Validates fields and uniqueness
        schema = ExtractionSchema(fields=data)

        # Persist schema data for the current demo session
        request.session["schema"] = schema.model_dump()
        return templates.TemplateResponse(
            request=request,
            name="schema_success.html",
            context={"schema": schema, **_provider_template_context(request)},
        )
    except ValidationError as e:
        # Pydantic validation errors
        errors = [
            f"Field error: {err['msg']} at {err.get('loc', [])}" for err in e.errors()
        ]
        return templates.TemplateResponse(
            request=request,
            name="schema_builder.html",
            context={
                "errors": errors,
                "raw_json": schema_data,
                "schema": request.session.get("schema", {}),
            },
        )
    except Exception as e:
        # Generic JSON or value errors
        return templates.TemplateResponse(
            request=request,
            name="schema_builder.html",
            context={
                "errors": [str(e)],
                "raw_json": schema_data,
                "schema": request.session.get("schema", {}),
            },
        )


@router.get("/extraction/provider", response_class=HTMLResponse)
async def provider_settings_form(request: Request):
    """Render provider selection settings."""
    return templates.TemplateResponse(
        request=request,
        name="provider_settings.html",
        context=_provider_template_context(request),
    )


@router.post("/extraction/provider", response_class=HTMLResponse)
async def save_provider_settings(
    request: Request,
    provider: Annotated[Optional[str], Form()] = None,
    google_api_key: Annotated[Optional[str], Form()] = None,
    google_model: Annotated[Optional[str], Form()] = None,
    ollama_model: Annotated[Optional[str], Form()] = None,
    ollama_base_url: Annotated[Optional[str], Form()] = None,
):
    """Save provider settings for the current demo session."""
    try:
        _save_provider_config(
            request,
            provider=provider,
            google_api_key=google_api_key,
            google_model=google_model,
            ollama_model=ollama_model,
            ollama_base_url=ollama_base_url,
        )
    except ProviderConfigError as exc:
        return templates.TemplateResponse(
            request=request,
            name="provider_settings.html",
            context={
                "errors": [str(exc)],
                **_provider_template_context(request),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="provider_settings.html",
        context={
            "saved": True,
            **_provider_template_context(request),
        },
    )


@router.post("/extraction/run", response_class=HTMLResponse)
async def run_extraction(
    request: Request,
    provider: Annotated[Optional[str], Form()] = None,
    google_api_key: Annotated[Optional[str], Form()] = None,
    google_model: Annotated[Optional[str], Form()] = None,
    ollama_model: Annotated[Optional[str], Form()] = None,
    ollama_base_url: Annotated[Optional[str], Form()] = None,
):
    """Run batch extraction using session-stored notes and schema."""
    notes_data = request.session.get("notes")
    schema_data = request.session.get("schema")

    errors = []
    if not notes_data:
        errors.append("No notes found. Please submit notes first.")
    if not schema_data:
        errors.append("No schema defined. Please create a schema first.")

    if errors:
        return templates.TemplateResponse(
            request=request,
            name="extraction_error.html",
            context={"errors": errors},
        )

    try:
        if provider is not None:
            _save_provider_config(
                request,
                provider=provider,
                google_api_key=google_api_key,
                google_model=google_model,
                ollama_model=ollama_model,
                ollama_base_url=ollama_base_url,
            )
        provider_config = provider_config_from_session(
            request.session.get("provider_config")
        )
        extraction_provider = build_provider(provider_config)
    except ProviderConfigError as exc:
        schema = ExtractionSchema(**schema_data)
        return templates.TemplateResponse(
            request=request,
            name="schema_success.html",
            context={
                "schema": schema,
                "errors": [str(exc)],
                **_provider_template_context(request),
            },
        )

    notes = [ClinicalNote(**n) for n in notes_data]
    schema = ExtractionSchema(**schema_data)

    service = BatchExtractionService(provider=extraction_provider)
    try:
        service.run(notes, schema)
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="extraction_error.html",
            context={"errors": [f"Extraction failed: {e}"]},
        )

    table = service.results_as_table(schema)
    session_config = request.session.get("provider_config")
    provider_config = provider_config_from_session(session_config)

    # Persist results in session for downstream review / export
    request.session["extraction_results"] = [r.model_dump() for r in service.results]
    request.session["extraction_status"] = service.status.value

    return templates.TemplateResponse(
        request=request,
        name="extraction_results.html",
        context={
            "table": table,
            "schema": schema,
            "note_count": len(notes),
            "status": service.status.value,
            "provider_label": PROVIDER_LABELS[provider_config.kind],
            **_provider_template_context(request),
        },
    )


@router.get("/extraction/results", response_class=HTMLResponse)
async def extraction_results(request: Request):
    """Display the most recent extraction results from the session."""
    results_data = request.session.get("extraction_results")
    schema_data = request.session.get("schema")

    if not results_data or not schema_data:
        return templates.TemplateResponse(
            request=request,
            name="extraction_error.html",
            context={
                "errors": ["No extraction results available. Run an extraction first."]
            },
        )

    schema = ExtractionSchema(**schema_data)
    columns = [field.name for field in schema.fields]
    rows = []
    for idx, r in enumerate(results_data):
        row = {"_note_index": idx + 1}
        for col in columns:
            row[col] = r["values"].get(col)
        rows.append(row)

    table = {"columns": columns, "rows": rows}
    status = request.session.get("extraction_status", "complete")

    session_config = request.session.get("provider_config")
    provider_config = provider_config_from_session(session_config)

    return templates.TemplateResponse(
        request=request,
        name="extraction_results.html",
        context={
            "table": table,
            "schema": schema,
            "note_count": len(results_data),
            "status": status,
            "provider_label": PROVIDER_LABELS[provider_config.kind],
            **_provider_template_context(request),
        },
    )


@router.get("/extraction/export")
async def export_extraction_results(request: Request):
    """Download extraction results as a CSV file."""
    results_data = request.session.get("extraction_results")
    schema_data = request.session.get("schema")

    if not results_data or not schema_data:
        return templates.TemplateResponse(
            request=request,
            name="extraction_error.html",
            context={
                "errors": ["No extraction results available. Run an extraction first."]
            },
        )

    schema = ExtractionSchema(**schema_data)
    results = [ExtractionResult(**r) for r in results_data]
    csv_content = export_results_to_csv(results, schema)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="extraction_results.csv"'
        },
    )

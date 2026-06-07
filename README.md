# Notaris

Notaris is a tool for extracting structured research data from free-text clinical notes, case reports, and EHR exports.

## Problem

Researchers often need to turn unstructured clinical text into analyzable datasets. A single note may contain the fields needed for a study, such as diagnosis, medications, lab values, demographics, treatment response, or follow-up outcomes, but extracting those fields manually is slow, repetitive, and inconsistent across reviewers.

## Solution

Notaris helps researchers upload or paste batches of clinical notes, define the fields they want to extract, and generate a spreadsheet-ready table from the source text.

Instead of forcing every study into a fixed template, Notaris is intended to support configurable extraction schemas. A researcher can choose the fields that matter for a project, for example:

- Age
- Primary diagnosis
- HbA1c value
- Drug name
- Medication dose
- Adverse event
- Outcome at 6 months

The resulting output is structured data that can be reviewed, corrected, exported, and analyzed.

## Intended Workflow

1. Paste or upload a batch of clinical notes.
2. Define the extraction schema for the study.
3. Run AI-assisted extraction across the note batch.
4. Review extracted values against the original text.
5. Export the result as a spreadsheet-ready table.

## Development

Notaris is a Python FastAPI application managed with `uv`.

Install dependencies:

```sh
uv sync --dev
```

Run the test suite:

```sh
uv run pytest
```

Run the local development server:

```sh
uv run notaris
```

The app starts at `http://127.0.0.1:8000`. A health check is available at
`http://127.0.0.1:8000/health`.

## Domain Models

The core domain layer defines typed Pydantic models for:

- `ClinicalNote`: source text plus optional metadata.
- `ExtractionField`: a named field with a description, supported type, and optional constraints.
- `ExtractionSchema`: a collection of extraction fields.
- `ExtractionResult`: extracted values associated with a source note.

Supported extraction field types are `string`, `integer`, `number`, `boolean`, and
`date`.

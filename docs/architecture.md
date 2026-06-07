# Project Architecture

## Project Stack

| Layer | Technology | Reason |
| --- | --- | --- |
| Web API | FastAPI | Python-native, typed request/response models|
| UI | Server-rendered templates with HTMX or a small frontend client | Keeps the demo focused on Python while still allowing an interactive review workflow. |
| Data validation | Pydantic | Strong schema validation for notes, extraction fields, and results. |
| Background work | In-process task runner for demo scope | Enough for batch extraction without introducing queue infrastructure. |
| AI provider integration | Provider adapter interface | Allows mock extraction, local fixtures, or an external LLM provider. |
| Export | pandas or standard CSV utilities | Straightforward spreadsheet-ready output. |
| Tests | pytest | Standard Python testing workflow. |


## Component Responsibilities

### Web App

The web app owns HTTP routing, form handling, template rendering, and API responses. It should not contain extraction rules, database queries, or provider-specific prompt logic.

### Domain Models

Domain models represent the concepts the application cares about:

- `ClinicalNote`: source text and metadata
- `ExtractionSchema`: study-specific collection of fields
- `ExtractionField`: name, description, type, and optional constraints
- `ExtractionResult`: extracted values


### AI Provider Layer

The provider layer isolates AI-specific behavior from the rest of the app.

At minimum, it should include:

- a `BaseExtractionProvider` interface
- a `MockExtractionProvider` for deterministic portfolio demos and tests
- an optional `LLMExtractionProvider` for real model-backed extraction

The mock provider is important because the demo should run without API keys, network access, or real clinical data.

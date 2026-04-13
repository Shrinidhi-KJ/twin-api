# Twin API — Mock API Generator from OpenAPI Specs

A tool that takes any OpenAPI 3.x specification and automatically generates a fully functional mock server — a "digital twin" of the original API. This enables AI agents and developers to safely build and test integrations against a sandbox before swapping to production.

## Motivation

When building integrations with third-party APIs (CRMs, payment systems, legacy services), developers often face two problems:

1. Many systems do not provide sandbox environments, forcing integration work to happen against live production APIs.
2. Manually building and maintaining mock servers for each third-party system is slow and does not scale across customers or systems.

Twin API solves this by generating a runnable mock directly from an OpenAPI spec, matching endpoints, schemas, and authentication flows so that integration code written against the mock works unchanged against the real API.

## Features

- Parses any OpenAPI 3.x specification
- Auto-generates FastAPI routes for every endpoint defined in the spec
- Recursively generates schema-valid fake data using rule-based heuristics and Faker
- Handles nested objects, enums, arrays, and `$ref` references
- In-memory persistence with full CRUD behaviour (GET, POST, PUT, PATCH, DELETE)
- Automatic Bearer token and API key authentication, enforced when the spec defines security schemes
- Interactive Swagger UI docs at `/docs` for every generated mock
- Works with any OpenAPI 3.x spec via a single command-line argument

## Usage

### Installation

```bash
python -m venv venv
source venv/bin/activate  # on macOS/Linux
.\venv\Scripts\activate   # on Windows PowerShell
pip install fastapi uvicorn pydantic prance openapi-spec-validator faker requests
```

### Running a mock

```bash
python run_mock.py <path-to-openapi-spec.json> [port]
```

Example:

```bash
python run_mock.py petstore.json
python run_mock.py petstore.json 9000
```

Visit `http://127.0.0.1:8000/docs` for the interactive API documentation.

### Example request

```bash
curl -H "Authorization: Bearer any-token-works" http://127.0.0.1:8000/pet/findByStatus?status=available
```

## How it works

1. **Spec parsing**: The OpenAPI spec is loaded and resolved, including all `$ref` pointers to nested schemas.
2. **Route generation**: For every path and method in the spec, a dynamic FastAPI route is registered. Specific routes (like `/pet/findByStatus`) are registered before parameterized routes (like `/pet/{petId}`) to avoid routing collisions.
3. **Fake data generation**: Each schema is recursively traversed. Simple types use Faker with field-name-aware heuristics (e.g. a field named `email` generates an email). Enums pick a valid value, arrays generate lists, and `$ref` fields recursively generate the referenced object.
4. **CRUD simulation**: An in-memory dict acts as the database per resource. GET retrieves, POST creates with an auto-assigned ID, PUT/PATCH updates, DELETE removes.
5. **Authentication**: If the spec defines `securitySchemes`, the mock enforces that an `Authorization` or `api_key` header is present. Any non-empty token is accepted, mirroring sandbox behaviour.

## Current limitations

- **OpenAPI 3.x only**: Swagger 2.0 specs load but no resources are seeded, as the schema paths differ (`definitions` vs `components.schemas`). A warning is printed in this case.
- **In-memory storage**: Data resets on server restart. Suitable for ephemeral sandboxes but not long-running testing.
- **Basic auth only**: Bearer tokens and API keys are accepted; OAuth2 flows are simulated structurally but not fully implemented.
- **Rule-based data generation**: Field-name heuristics produce realistic data in most cases, but semantically rich content (e.g. domain-specific vocabulary) would benefit from LLM-based generation in a future version.

## Future work

- LLM-backed data generation for fields where simple heuristics fall short
- Swagger 2.0 adapter layer
- Full OAuth2 flow simulation
- Persistent storage backend option (SQLite)
- Dockerised deployment
- Automated evaluation harness to test whether AI-generated integration code against the mock works unchanged against production

## Tech stack

Python 3.11, FastAPI, Pydantic, Uvicorn, Faker, Prance.

## Author

[Your name] — MSc Artificial Intelligence, University of Stirling.
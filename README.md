# Serial LinkedIn Killer

Agent system for automating LinkedIn job applications and employee outreach. Three-layer architecture: CLI → Core Agent API (FastAPI + Kafka) → LinkedIn MCP Server (Selenium).

<p align="center">
  <img src="assets/logo.png" alt="Serial LinkedIn Killer Logo" width="900">
</p>

## Architecture

```
CLI (local)
  ├── HTTP POST → Core Agent API (Docker) → returns task_id
  │                  ├── JobApplicationAgent (LangGraph)
  │                  └── EmployeeOutreachAgent (LangGraph)
  │                        ↓
  │                  Kafka Producer → [job-results / outreach-results]
  │                        ↓
  └── Kafka Consumer ← receives results
                              ↓
                  LinkedIn MCP Server (Docker) → Selenium browser automation
```

**Services (docker-compose):**
- `kafka` — KRaft mode, message broker
- `core-agent` — FastAPI API on port 8080, orchestrates workflows
- `linkedin-mcp-server` — FastMCP server on port 3000, browser automation

## Quick Start

```bash
# Install
poetry install

# Set credentials
export LINKEDIN_EMAIL="your-email"
export LINKEDIN_PASSWORD="your-password"

# Import company dataset into SQLite (one-time, for outreach)
poetry run python scripts/cli.py import-dataset

# Start services
docker compose up -d

# Run CLI
poetry run python scripts/cli.py --help
```

## Outreach Workflow (Two-Phase)

The outreach workflow uses role-based clustering to target employees by job function:

```
Phase 1: Search & Cluster (synchronous)
  ├── Filter companies by industry/country/size
  ├── Search employees at each company via LinkedIn
  └── Cluster employees by role using LLM classification
        ↓
  Role Groups: Engineering, Finance, Sales, Marketing, HR/People, Operations, Executive, Other
        ↓
Phase 2: Message (async via Kafka)
  ├── User selects which role groups to message
  ├── User provides different templates per role group
  └── Agent sends messages with per-group personalization
```

**Interactive CLI flow:**
```bash
poetry run python scripts/cli.py outreach --interactive

# 1. Select company filters (industry, country, size)
# 2. API searches employees and clusters by role
# 3. See role groups with employee counts
# 4. Select which groups to message
# 5. Enter message template for each group
# 6. Preview and confirm
# 7. Messages sent, results displayed by role
```

## CLI Commands

```bash
# Job application workflow
poetry run python scripts/cli.py run

# Employee outreach (interactive, two-phase)
poetry run python scripts/cli.py outreach --interactive

# Outreach with config (non-interactive)
poetry run python scripts/cli.py outreach --no-interactive

# Warm-up mode (cap at 10 messages)
poetry run python scripts/cli.py outreach --warmup

# Import company CSV into SQLite
poetry run python scripts/cli.py import-dataset

# Test API connection
poetry run python scripts/cli.py test-connection

# Init/validate config
poetry run python scripts/cli.py init
poetry run python scripts/cli.py validate
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/jobs/apply` | Submit job application workflow |
| `GET` | `/api/outreach/filters` | Get filter values (industry, country, size) |
| `POST` | `/api/outreach/search` | Phase 1: Search employees, cluster by role (sync) |
| `POST` | `/api/outreach/send` | Phase 2: Send messages to selected groups (async) |
| `POST` | `/api/outreach/run` | Legacy: Single-phase outreach (async) |

**Phase 1 - Search & Cluster:**
```bash
curl -X POST http://localhost:8080/api/outreach/search \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {"industry": ["Technology"], "country": ["United States"]},
    "credentials": {"email": "...", "password": "..."}
  }'

# Response:
# {
#   "session_id": "uuid",
#   "role_groups": {
#     "Engineering": [{"name": "...", "title": "...", "profile_url": "..."}],
#     "Sales": [...],
#     ...
#   },
#   "total_employees": 42,
#   "companies_processed": 5
# }
```

**Phase 2 - Send Messages:**
```bash
curl -X POST http://localhost:8080/api/outreach/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-from-phase-1",
    "selected_groups": {
      "Engineering": {
        "enabled": true,
        "message_template": "Hi {employee_name}, I saw you work at {company_name}...",
        "template_variables": {"my_name": "John", "my_role": "Recruiter"}
      },
      "Sales": {
        "enabled": true,
        "message_template": "Hello {employee_name}, I have an opportunity...",
        "template_variables": {"my_name": "John"}
      }
    },
    "credentials": {"email": "...", "password": "..."},
    "warm_up": false
  }'

# Response: { "task_id": "uuid" }
# Results delivered via Kafka topic: outreach-results
```

## Configuration

All config lives in `config/agent.yaml`:

```yaml
llm:
  base_url: "http://localhost:8088/v1"
  api_key: "not-needed"
  temperature: 0.1

mcp_server:
  host: "localhost"
  port: 8000

outreach:
  dataset_path: "./data/free_company_dataset.csv"
  db_path: "./data/companies.db"
  employees_per_company: 10
  daily_message_limit: 50
  delay_between_messages_min: 30.0
  delay_between_messages_max: 120.0

kafka:
  bootstrap_servers: "localhost:9092"

api:
  host: "0.0.0.0"
  port: 8080
```

Environment variables override config: `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`, `KAFKA_BOOTSTRAP_SERVERS`, `LOCAL_LLM_BASE_URL`, `MCP_SERVER_HOST`, `MCP_SERVER_PORT`.

## CV Data

Structured JSON at `data/cv_data.json`:

```json
{
  "name": "string",
  "work_experience": [
    { "title": "string", "company": "string", "start_date": "MM-YYYY", "end_date": "MM-YYYY", "stack": ["string"] }
  ],
  "education": [{ "title": "string", "institution": "string" }],
  "skills": [{ "title": "string", "level": "Advanced|Intermediate|Basic" }],
  "languages": [{ "title": "string", "level": "Native|Fluent|Intermediate|Basic" }]
}
```

## Company Dataset

CSV at `data/free_company_dataset.csv`, imported into SQLite via `import-dataset` command.

| Column | Example |
|--------|---------|
| `name` | `acme corp` |
| `industry` | `software` |
| `country` | `united states` |
| `size` | `51-200` |
| `linkedin_url` | `linkedin.com/company/acme` |
| `locality` | `san francisco` |

## Role Categories

The LLM clusters employee job titles into these categories:

| Category | Example Titles |
|----------|----------------|
| Engineering | Software Engineer, DevOps, Architect, QA |
| Finance | CFO, Financial Analyst, Controller, Accountant |
| Sales | Sales Rep, Account Executive, SDR, Business Dev |
| Marketing | Marketing Manager, Content, Growth, Brand |
| HR/People | Recruiter, Talent Acquisition, People Ops |
| Operations | Project Manager, Program Manager, Supply Chain |
| Executive | CEO, CTO, VP, Director, Head of |
| Other | Unclassified titles |

## Development

```bash
poetry install
poetry run pytest tests/
```

## License

Educational and research purposes. Ensure compliance with LinkedIn's Terms of Service.

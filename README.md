# LinkedIn Job Application & Outreach Automation

AI-powered system for automating LinkedIn job applications and employee outreach. Three-layer architecture: CLI → Core Agent API (FastAPI + Kafka) → LinkedIn MCP Server (Selenium).

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

## CLI Commands

```bash
# Job application workflow
poetry run python scripts/cli.py run

# Employee outreach (interactive TUI)
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
| `POST` | `/api/outreach/run` | Submit outreach workflow |

POST endpoints return `{ task_id }` immediately. Results are published to Kafka topics.

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

## Development

```bash
poetry install
poetry run pytest tests/
```

## License

Educational and research purposes. Ensure compliance with LinkedIn's Terms of Service.

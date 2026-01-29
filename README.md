# LinkedIn Job Application Automation System

A comprehensive AI-powered system for automating LinkedIn job applications using FastMCP, LangGraph, and intelligent form filling.

## Architecture

The system uses a **single-container architecture** with Hugging Face Serverless API for cloud-based AI inference:

### Core Job Application Agent (`core-agent` container)
- **MCP Client**: Uses official `mcp` SDK with stdio transport for protocol communication
- **MCP Server**: LinkedIn server runs as subprocess via stdio (not HTTP)
- **LangGraph Workflow**: Orchestrates the complete job application process
- **CV Analysis**: AI-powered PDF CV reading and structured data extraction
- **Job Filtering**: Intelligent job matching based on CV profile alignment
- **RPA Automation**: Selenium-based LinkedIn interaction with anti-detection
- **AI Form Filling**: Uses Hugging Face Serverless API for intelligent form completion

### AI Inference
- **Hugging Face Serverless API**: Cloud-based inference with Qwen3-30B-A3B-Thinking
- **No GPU Required**: Serverless inference eliminates infrastructure complexity
- **Scalable**: Automatic scaling and high availability
- **Cost Effective**: Pay-per-use pricing model

## Features

 **AI-Powered CV Analysis**: Extracts skills, experience, education from PDF CVs
 **Intelligent Job Search**: Multi-criteria LinkedIn job searching with pagination
 **Smart Job Filtering**: AI-based job relevance scoring using CV profile
 **Advanced Form Filling**: AI handles dynamic LinkedIn application forms
 **Anti-Detection RPA**: Randomized delays and user-agent rotation
 **Containerized Architecture**: Scalable Docker-based deployment
 **Error Handling**: Comprehensive error recovery and logging

## CV Data Structure

The system uses a structured JSON format for CV data located at `/data/cv_data.json`. This replaces PDF CV processing and enables more precise job matching.

### CV JSON Schema

```json
{
  "name": "string",
  "email": "string",
  "location": "string",
  "phone": "string",
  "work_experience": [
    {
      "title": "string",
      "company": "string",
      "start_date": "MM-YYYY",
      "end_date": "MM-YYYY",
      "description": "string",
      "stack": ["string", "string", ...]
    }
  ],
  "education": [
    {
      "title": "string",
      "institution": "string",
      "start_date": "MM-YYYY",
      "end_date": "MM-YYYY"
    }
  ],
  "certifications": [
    {
      "title": "string",
      "institution": "string",
      "start_date": "MM-YYYY",
      "end_date": "MM-YYYY"
    }
  ],
  "languages": [
    {
      "title": "string",
      "level": "Native|Fluent|Intermediate|Basic"
    }
  ],
  "skills": [
    {
      "title": "string",
      "level": "Advanced|Intermediate|Basic"
    }
  ]
}
```

### Example CV Data

```json
{
  "name": "Joan Canossa",
  "email": "joan.canossa@example.com",
  "location": "Ciudad Autónoma de Buenos Aires, Argentina.",
  "phone": "(+54) 112171370",
  "work_experience": [
    {
      "title": "Software Engineer",
      "company": "Mercado Libre",
      "start_date": "11-2024",
      "end_date": "11-2025",
      "description": "Designed and developed the integration of a robotics orchestration system...",
      "stack": ["Java", "Spring", "JavaScript", "TypeScript", "MySQL", "Python"]
    }
  ],
  "education": [
    {
      "title": "Bachelor's Degree in Information Technology Management",
      "institution": "UADE",
      "start_date": "08-2024",
      "end_date": "06-2025"
    }
  ],
  "skills": [
    {
      "title": "Java",
      "level": "Advanced"
    }
  ]
}
```

### Benefits of JSON CV Format

- **Structured Data**: Precise field extraction without AI parsing errors
- **Technology Stack Matching**: Direct technology comparison for job filtering
- **Experience Calculation**: Automatic years of experience computation
- **Skill Level Matching**: Granular skill level comparison with job requirements
- **Performance**: Instant CV loading vs. slow PDF processing
- **Consistency**: Deterministic CV data across multiple job applications

## Usage Options

### 🖥️ Terminal Client (Recommended)
Interactive command-line interface with rich formatting and real-time progress.

```bash
# Quick start with interactive setup
python job_applier.py run --interactive

# Use configuration file
python job_applier.py run --config ./examples/config.yaml

# Initialize configuration
python job_applier.py init
```

### 🐳 Docker Deployment
Full containerized deployment with MCP server architecture.

```bash
# Build and start services
docker-compose up -d
```

## Quick Start

### Prerequisites
- Python 3.12+ (for terminal client) OR Docker and Docker Compose
- LinkedIn account credentials
- PDF CV file
- Hugging Face account and API token (for serverless inference)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd serial-job-applier
```

### 2. Terminal Client Setup (Quick Start)

```bash
# Install dependencies
pip install poetry
poetry install

# Set environment variables (recommended for security)
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
export CV_FILE_PATH="./data/cv.pdf"
export HUGGING_FACE_HUB_TOKEN="your-hf-token"
export MCP_SERVER_HOST="localhost"  # Optional - defaults to localhost
export MCP_SERVER_PORT="3000"       # Optional - defaults to 3000

# Or use .env file
cp .env.example .env
# Edit .env with your actual values

# Place your CV file
cp /path/to/your/cv.pdf data/cv.pdf

# Run interactive setup
python job_applier.py run --interactive
```

### 3. Docker Setup (Full System)
Create `.env` file:
```bash
LINKEDIN_EMAIL=your-email@example.com
LINKEDIN_PASSWORD=your-password
CV_FILE_PATH=/app/data/cv.pdf
HUGGING_FACE_HUB_TOKEN=your-hf-token-here
```

### 3. Prepare CV File
```bash
mkdir -p data
cp /path/to/your/cv.pdf data/cv.pdf
```

### 4. Start the System
```bash
# Build and start the core agent
docker-compose up -d

# Check core agent logs
docker-compose logs -f core-agent
```

### 5. The job application workflow runs automatically when the container starts

## Terminal Client Features

### 🎯 Command Overview
- **`run`**: Execute the complete job application workflow
- **`outreach`**: Run the employee outreach workflow (filter companies, find employees, send messages)
- **`init`**: Create and configure a new configuration file
- **`validate`**: Validate configuration files
- **`test-connection`**: Test MCP server connectivity

### 🎨 Output Formats
- **Rich**: Beautiful terminal UI with colors, progress bars, and tables
- **Simple**: Plain text output for logging and scripting
- **JSON**: Machine-readable output for automation

### 📋 Configuration Management
- **YAML Configuration**: Human-readable configuration files
- **Environment Variables**: Secure credential management
- **Interactive Setup**: Step-by-step configuration wizard
- **Validation**: Comprehensive configuration validation

### 📊 Progress Tracking
- **Real-time Status**: Live workflow progress updates
- **Results Storage**: Automatic saving of workflow results
- **Error Reporting**: Detailed error analysis and troubleshooting
- **Logging**: Configurable logging for debugging

### 🔧 Usage Examples

```bash
# Interactive job search setup
python job_applier.py run --interactive

# Use configuration file
python job_applier.py run --config ./examples/config.yaml

# JSON output for automation
python job_applier.py run --format json --save

# Test MCP server connection
python job_applier.py test-connection --mcp-host localhost --mcp-port 3000

# Create configuration file
python job_applier.py init --config ./my-config.yaml
```

For detailed CLI usage, see [CLI_USAGE.md](CLI_USAGE.md).

## Employee Outreach

Automated LinkedIn employee outreach: filter companies from a dataset, find employees at each company, and send personalized messages or connection requests.

### Quick Start

```bash
python job_applier.py outreach --interactive
```

### TUI Interactive Flow

The `outreach` command walks you through each step:

**1. Company Filtering**

The TUI loads `data/free_company_dataset.csv` and presents filterable columns as numbered tables:

```
Available Industry values
┌────┬─────────────────────────────┐
│ #  │ Industry                    │
├────┼─────────────────────────────┤
│ 1  │ automotive                  │
│ 2  │ hospital & health care      │
│ 3  │ investment banking          │
│ 4  │ software                    │
│ ...│ ...                         │
└────┴─────────────────────────────┘
Select industry (comma-separated numbers, or 'all'): 4

Available Country values
┌────┬─────────────────┐
│ #  │ Country         │
├────┼─────────────────┤
│ 1  │ germany         │
│ 2  │ united states   │
│ ...│ ...             │
└────┴─────────────────┘
Select country (comma-separated numbers, or 'all'): 1,2

Available Size values
┌────┬──────────┐
│ #  │ Size     │
├────┼──────────┤
│ 1  │ 1-10     │
│ 2  │ 11-50    │
│ 3  │ 51-200   │
│ 4  │ 201-500  │
└────┴──────────┘
Select size (comma-separated numbers, or 'all'): 3,4
```

After filtering, a summary table is shown for confirmation.

**2. Message Template**

Enter your message inline (end with an empty line) or provide a file path:

```
Enter message template. Use {employee_name}, {company_name},
{employee_title}, {my_name}, {my_role} as placeholders.

Hi {employee_name},

I noticed you work at {company_name} as {employee_title}.
I'm {my_name}, a {my_role}, and I'd love to connect
regarding {topic}.

{custom_closing}

```

The TUI then prompts for static variables (`my_name`, `my_role`, `topic`, `custom_closing`) and shows a rendered preview before confirming.

**3. Execution**

The agent iterates through each filtered company:
- Navigates to `linkedin.com/company/<name>/people/`
- Scrapes employee cards (name, title, profile URL)
- For each employee, visits their profile and either:
  - Sends a **direct message** (if Message button available)
  - Sends a **connection request with note** (if Connect button available, message truncated to 300 chars)
- Randomized delays between messages (30-120s, configurable)

### Configuration

All settings live in `config/agent.yaml`:

```yaml
outreach:
  dataset_path: "./data/free_company_dataset.csv"
  message_template_path: ""         # or path to .txt template file
  message_template: ""              # or inline template
  employees_per_company: 10
  daily_message_limit: 50
  delay_between_messages_min: 30.0
  delay_between_messages_max: 120.0
  filters:
    industry: []     # pre-set filters (skip TUI selection)
    country: []
    size: []
```

### CLI Options

```bash
# Interactive mode (default) — TUI for filtering and template
python job_applier.py outreach --interactive

# Non-interactive — uses filters and template from config/agent.yaml
python job_applier.py outreach --config config/agent.yaml --no-interactive

# Warm-up mode — caps at 10 messages (for new accounts)
python job_applier.py outreach --warm-up
```

### Dataset Columns

The CSV at `data/free_company_dataset.csv` has these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `country` | Company country | `united states` |
| `industry` | Business sector | `software` |
| `size` | Employee range | `51-200` |
| `linkedin_url` | Company LinkedIn URL | `linkedin.com/company/acme` |
| `name` | Company name | `acme corp` |
| `locality` | City | `san francisco` |
| `region` | State/region | `california` |
| `founded` | Year founded | `2010` |
| `website` | Company website | `acme.com` |

## System Components

### MCP Tools
- **`search_jobs`**: LinkedIn job search with Easy Apply filtering
- **`easy_apply_for_jobs`**: AI-powered job application with form filling
- **`search_employees`**: Find employees at a company via their LinkedIn company page
- **`send_message`**: Send a direct message or connection request to a LinkedIn user

### Core Services
- **`JobApplicationAgent`**: Main orchestration agent with LangGraph workflow
- **`LinkedInMCPClient`**: HTTP client for MCP protocol communication
- **`EasyApplyAgent`**: AI form analysis and filling agent
- **`BrowserManager`**: Selenium automation with anti-detection

### AI Models
- **Qwen3-30B-A3B-Thinking**: Advanced reasoning model via Hugging Face Serverless API
- **Serverless Inference**: Cloud-based high-performance inference
- **PDF Processing**: PyPDF2 and pdfplumber for CV text extraction

## CV Data Structure

The system processes CVs by converting PDFs to structured JSON data that follows this schema:

```json
{
  "name": "string",
  "email": "string",
  "location": "string",
  "phone": "string",
  "work_experience": [
    {
      "title": "string",
      "company": "string",
      "start_date": "string",
      "end_date": "string",
      "description": "string",
      "stack": ["string"]
    }
  ],
  "education": [
    {
      "title": "string",
      "institution": "string",
      "start_date": "string",
      "end_date": "string"
    }
  ],
  "certifications": [
    {
      "title": "string",
      "institution": "string",
      "start_date": "string",
      "end_date": "string"
    }
  ],
  "languages": [
    {
      "title": "string",
      "level": "string"
    }
  ],
  "skills": [
    {
      "title": "string",
      "level": "string"
    }
  ]
}
```

This structured data is used for intelligent job matching and application personalization.

## Workflow

1. **CV Analysis**: Extract and structure data from PDF CV
2. **Job Search**: Multi-criteria LinkedIn search via MCP protocol
3. **Job Filtering**: AI-powered relevance scoring based on CV profile
4. **Application**: Intelligent form filling for each selected job
5. **Results**: Comprehensive reporting of application outcomes

## Dependencies

- **Core**: Python 3.12, LangGraph, LangChain, FastMCP
- **RPA**: Selenium, undetected-chromedriver, BeautifulSoup4
- **AI**: Hugging Face Serverless API (Qwen3-30B-A3B-Thinking), LangChain-HuggingFace
- **PDF**: PyPDF2, pdfplumber
- **Infrastructure**: Docker

## License

This project is for educational and research purposes. Ensure compliance with LinkedIn's Terms of Service and applicable laws when using automated tools.

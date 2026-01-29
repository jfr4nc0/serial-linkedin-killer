"""Main CLI client for the LinkedIn Job Application Agent."""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import typer
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from src.cli.config import CLIConfig, JobSearchConfig
from src.cli.ui import TerminalUI
from src.core.utils.logging_config import (
    configure_core_agent_logging,
    get_core_agent_logger,
)


class JobApplicationCLI:
    """Command-line interface for the LinkedIn Job Application Agent."""

    def __init__(self):
        load_dotenv()
        configure_core_agent_logging()

        self.app = typer.Typer(
            name="job-applier",
            help="LinkedIn Job Application Agent - Automated job search and application system",
            no_args_is_help=True,
            rich_markup_mode=None,
        )
        self.ui = None
        self.config = None

        self._register_commands()

    def _get_api_base_url(self) -> str:
        """Get the core-agent API base URL from config."""
        from src.config.config_loader import load_config

        config = load_config()
        host = os.getenv("CORE_AGENT_HOST", config.api.host)
        port = os.getenv("CORE_AGENT_PORT", str(config.api.port))
        # For CLI connecting from outside Docker, default to localhost
        if host == "0.0.0.0":
            host = "localhost"
        return f"http://{host}:{port}"

    def _get_kafka_servers(self) -> str:
        """Get Kafka bootstrap servers from config."""
        from src.config.config_loader import load_config

        config = load_config()
        return os.getenv("KAFKA_BOOTSTRAP_SERVERS", config.kafka.bootstrap_servers)

    def _register_commands(self):
        """Register all CLI commands."""

        @self.app.command("run")
        def run_workflow():
            """Run the job application workflow."""
            self._run_workflow_command(
                None, None, None, None, "localhost", 3000, "rich", True, False
            )

        @self.app.command("init")
        def init_config():
            """Initialize a new configuration file."""
            self._init_config_command(None, True)

        @self.app.command("validate")
        def validate_config():
            """Validate a configuration file."""
            self._validate_config_command(None)

        @self.app.command("test-connection")
        def test_connection():
            """Test connection to the core-agent API."""
            self._test_connection_command()

        @self.app.command("outreach")
        def outreach(
            config_file: str = typer.Option(
                "", "--config", "-c", help="Path to agent config YAML"
            ),
            interactive: bool = typer.Option(
                True, "--interactive/--no-interactive", help="Interactive mode"
            ),
            warmup: bool = typer.Option(
                False, "--warmup", is_flag=True, help="Warm-up mode: cap at 10 messages"
            ),
        ):
            """Run the employee outreach workflow."""
            self._run_outreach_command(config_file or None, interactive, warmup)

        @self.app.command("import-dataset")
        def import_dataset(
            csv_path: str = typer.Option(
                "", "--csv", help="Path to CSV file (default from config)"
            ),
            db_path: str = typer.Option(
                "", "--db", help="Path to SQLite DB (default from config)"
            ),
        ):
            """Import company CSV dataset into SQLite for fast querying."""
            self._import_dataset_command(csv_path or None, db_path or None)

    def _import_dataset_command(self, csv_path: Optional[str], db_path: Optional[str]):
        """Import the company CSV into SQLite."""
        from src.config.config_loader import load_config
        from src.core.tools.company_db import CompanyDB

        self.ui = TerminalUI("rich")
        config = load_config()

        csv_path = csv_path or config.outreach.dataset_path
        db_path = db_path or config.outreach.db_path

        self.ui.console.print(
            f"Importing [bold]{csv_path}[/bold] into [bold]{db_path}[/bold]..."
        )

        db = CompanyDB(db_path)
        try:
            total = db.import_csv(
                csv_path,
                on_progress=lambda n: self.ui.console.print(
                    f"  {n:,} rows imported...", end="\r"
                ),
            )
            self.ui.console.print(f"\nImport complete: {total:,} rows", style="green")
        finally:
            db.close()

    def _run_workflow_command(
        self,
        config_file: Optional[str],
        linkedin_email: Optional[str],
        linkedin_password: Optional[str],
        cv_file: Optional[str],
        mcp_host: str,
        mcp_port: int,
        output_format: str,
        save_results: bool,
        interactive: bool,
    ):
        """Execute the run workflow command via API + Kafka."""
        try:
            self.ui = TerminalUI(output_format)
            self.ui.print_header()
            self.ui.start_timer()

            # Load configuration
            self.config = self._load_configuration(
                config_file,
                linkedin_email,
                linkedin_password,
                cv_file,
                mcp_host,
                mcp_port,
                output_format,
                save_results,
            )

            if not self.config.job_searches:
                self._interactive_job_search_setup()

            missing_fields = self.config.validate_required_fields()
            if missing_fields:
                self.ui.console.print(
                    f"Missing required configuration: {', '.join(missing_fields)}",
                    style="red",
                )
                sys.exit(1)

            self.ui.print_config_summary(self.config)
            self.ui.print_job_searches(self.config.job_searches)

            # Build API request
            job_searches = [
                {
                    "job_title": s.job_title,
                    "location": s.location,
                    "monthly_salary": s.monthly_salary,
                    "limit": s.limit,
                }
                for s in self.config.job_searches
            ]

            payload = {
                "job_searches": job_searches,
                "credentials": {
                    "email": self.config.linkedin_email,
                    "password": self.config.linkedin_password,
                },
                "cv_data_path": self.config.cv_file_path or "./data/cv_data.json",
            }

            # Submit to API
            base_url = self._get_api_base_url()
            self.ui.console.print(f"Submitting to {base_url}/api/jobs/apply...")

            with httpx.Client(timeout=30) as client:
                resp = client.post(f"{base_url}/api/jobs/apply", json=payload)
                resp.raise_for_status()
                task_id = resp.json()["task_id"]

            self.ui.console.print(f"Task submitted: {task_id}\n", style="green")

            # Consume results from Kafka
            from rich.live import Live
            from rich.spinner import Spinner
            from rich.text import Text

            from src.core.api.schemas.job_schemas import JobApplyResponse
            from src.core.kafka.consumer import KafkaResultConsumer
            from src.core.kafka.producer import TOPIC_JOB_RESULTS

            consumer = KafkaResultConsumer(bootstrap_servers=self._get_kafka_servers())

            with Live(
                Spinner("dots", text="Waiting for results..."),
                console=self.ui.console,
            ) as live:
                result = consumer.consume(
                    TOPIC_JOB_RESULTS, task_id, JobApplyResponse, timeout=600.0
                )
                live.update(Text("Workflow completed!", style="bold green"))

            if result is None:
                self.ui.console.print("Timed out waiting for results.", style="red")
                sys.exit(1)

            # Display results
            final_state = result.model_dump()
            self._handle_workflow_results(final_state)

        except KeyboardInterrupt:
            self.ui.console.print("\nWorkflow interrupted by user", style="red")
            sys.exit(1)
        except Exception as e:
            if self.ui:
                self.ui.console.print(f"Workflow failed: {str(e)}", style="red")
            logger.exception("Workflow execution failed")
            sys.exit(1)

    def _init_config_command(self, config_file: Optional[str], interactive: bool):
        """Execute the init config command."""
        self.ui = TerminalUI("rich")

        if not config_file:
            config_file = CLIConfig().get_default_config_path()

        if os.path.exists(config_file):
            overwrite = typer.confirm(
                f"Configuration file {config_file} already exists. Overwrite?"
            )
            if not overwrite:
                self.ui.console.print("Configuration initialization cancelled")
                return

        if interactive:
            config = self._create_interactive_config()
        else:
            config = self._create_default_config()

        config.save_to_file(config_file)
        self.ui.console.print(f"Configuration saved to {config_file}", style="green")

    def _validate_config_command(self, config_file: Optional[str]):
        """Execute the validate config command."""
        self.ui = TerminalUI("rich")

        if not config_file:
            config_file = CLIConfig().get_default_config_path()

        try:
            config = CLIConfig.load_from_file(config_file)
            config = config.merge_with_env()
            missing_fields = config.validate_required_fields()

            if missing_fields:
                self.ui.console.print("Configuration validation failed:", style="red")
                for field in missing_fields:
                    self.ui.console.print(f"  - Missing: {field}", style="red")
            else:
                self.ui.console.print("Configuration is valid", style="green")
                self.ui.print_config_summary(config)

        except Exception as e:
            self.ui.console.print(
                f"Configuration validation failed: {str(e)}", style="red"
            )

    def _test_connection_command(self):
        """Test connection to the core-agent API."""
        self.ui = TerminalUI("rich")
        base_url = self._get_api_base_url()

        self.ui.console.print(f"Testing connection to {base_url}...")

        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{base_url}/health")
                resp.raise_for_status()
            self.ui.console.print("Connection successful", style="green")
        except Exception as e:
            self.ui.console.print(f"Connection failed: {str(e)}", style="red")
            self.ui.console.print("Make sure the core-agent API is running.")

    def _load_configuration(
        self,
        config_file: Optional[str],
        linkedin_email: Optional[str],
        linkedin_password: Optional[str],
        cv_file: Optional[str],
        mcp_host: str,
        mcp_port: int,
        output_format: str,
        save_results: bool,
    ) -> CLIConfig:
        """Load and merge configuration from various sources."""
        config = CLIConfig(
            mcp_server_host=mcp_host,
            mcp_server_port=mcp_port,
            output_format=output_format,
            save_results=save_results if save_results is not None else True,
        )

        if not config_file:
            default_config = CLIConfig().get_default_config_path()
            if os.path.exists(default_config):
                config_file = default_config

        if config_file and os.path.exists(config_file):
            file_config = CLIConfig.load_from_file(config_file)
            config = file_config.copy(
                update={
                    "mcp_server_host": mcp_host,
                    "mcp_server_port": mcp_port,
                    "output_format": output_format,
                    "save_results": save_results,
                }
            )
        elif config_file:
            self.ui.console.print(
                f"Configuration file {config_file} not found, using defaults",
                style="yellow",
            )

        config = config.merge_with_env()

        if linkedin_email:
            config.linkedin_email = linkedin_email
        if linkedin_password:
            config.linkedin_password = linkedin_password
        if cv_file:
            config.cv_file_path = cv_file

        return config

    def _interactive_job_search_setup(self):
        """Interactive setup for job search criteria."""
        self.ui.console.print("Interactive Job Search Setup", style="bold blue")

        job_searches = []
        while True:
            self.ui.console.print(f"Configuring job search #{len(job_searches) + 1}:")

            job_title = self.ui.prompt_user_input("Job title", "Software Engineer")
            location = self.ui.prompt_user_input("Location", "Remote")
            salary_str = self.ui.prompt_user_input("Monthly salary (USD)", "5000")
            limit_str = self.ui.prompt_user_input("Job limit", "20")

            try:
                salary = int(salary_str)
                limit = int(limit_str)

                job_search = JobSearchConfig(
                    job_title=job_title,
                    location=location,
                    monthly_salary=salary,
                    limit=limit,
                )
                job_searches.append(job_search)

                self.ui.console.print(
                    f"Added job search: {job_title} in {location}", style="green"
                )

                if not typer.confirm("Add another job search?"):
                    break

            except ValueError as e:
                self.ui.console.print(f"Invalid input: {str(e)}", style="red")

        self.config.job_searches = job_searches

    def _create_interactive_config(self) -> CLIConfig:
        """Create configuration interactively."""
        self.ui.console.print("Interactive Configuration Setup", style="bold blue")

        linkedin_email = self.ui.prompt_user_input("LinkedIn email")
        linkedin_password = self.ui.prompt_user_input("LinkedIn password")
        cv_file_path = self.ui.prompt_user_input(
            "CV data JSON path", "./data/cv_data.json"
        )

        config = CLIConfig(
            linkedin_email=linkedin_email,
            linkedin_password=linkedin_password,
            cv_file_path=cv_file_path,
        )

        self.config = config
        self._interactive_job_search_setup()

        return self.config

    def _create_default_config(self) -> CLIConfig:
        """Create a default configuration."""
        return CLIConfig(
            job_searches=[
                JobSearchConfig(
                    job_title="Software Engineer",
                    location="Remote",
                    monthly_salary=5000,
                    limit=20,
                ),
                JobSearchConfig(
                    job_title="Software Engineer",
                    location="San Francisco",
                    monthly_salary=7000,
                    limit=15,
                ),
            ]
        )

    def _handle_workflow_results(self, final_state: Dict[str, Any]):
        """Handle and display workflow results."""
        if final_state.get("cv_analysis"):
            self.ui.print_cv_analysis(final_state["cv_analysis"])

        if final_state.get("all_found_jobs"):
            self.ui.print_job_results(final_state["all_found_jobs"])

        if final_state.get("application_results"):
            self.ui.print_application_results(final_state["application_results"])

        if final_state.get("errors"):
            self.ui.print_errors(final_state["errors"])

        self.ui.print_final_summary(final_state)

        if self.config and self.config.save_results:
            self._save_results(final_state)

    def _save_results(self, final_state: Dict[str, Any]):
        """Save workflow results to file."""
        try:
            results_dir = Path(self.config.results_directory)
            results_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"job_application_results_{timestamp}.json"
            filepath = results_dir / filename

            clean_state = {
                k: v for k, v in final_state.items() if k not in ["cv_content"]
            }

            with open(filepath, "w") as f:
                json.dump(clean_state, f, indent=2, default=str)

            self.ui.console.print(f"Results saved to {filepath}", style="blue")

        except Exception as e:
            self.ui.console.print(f"Failed to save results: {str(e)}", style="yellow")

    def _run_outreach_command(
        self,
        config_file: Optional[str],
        interactive: bool,
        warm_up: bool,
    ):
        """Execute the outreach workflow command via API + Kafka."""
        from src.core.tools.message_template import render_template

        try:
            self.ui = TerminalUI("rich")
            self.ui.start_timer()

            from src.config.config_loader import load_config

            config = load_config(config_file)
            base_url = self._get_api_base_url()

            self.ui.console.print(
                Panel(
                    "LinkedIn Employee Outreach Agent",
                    subtitle="Automated employee messaging system",
                    border_style="blue",
                )
            )
            self.ui.console.print()

            # Fetch filter options from API
            self.ui.console.print("Loading filter options from API...")
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{base_url}/api/outreach/filters")
                resp.raise_for_status()
                filter_data = resp.json()

            total_count = filter_data["total_companies"]
            self.ui.console.print(
                f"Loaded [bold green]{total_count}[/bold green] companies\n"
            )

            # Interactive filtering
            filters = {}
            if interactive:
                industries = filter_data["industries"]
                if industries:
                    selected = self.ui.print_company_filter_menu("industry", industries)
                    if selected:
                        filters["industry"] = selected

                countries = filter_data["countries"]
                if countries:
                    selected = self.ui.print_company_filter_menu("country", countries)
                    if selected:
                        filters["country"] = selected

                sizes = filter_data["sizes"]
                if sizes:
                    selected = self.ui.print_company_filter_menu("size", sizes)
                    if selected:
                        filters["size"] = selected
            else:
                if config.outreach.filters.industry:
                    filters["industry"] = config.outreach.filters.industry
                if config.outreach.filters.country:
                    filters["country"] = config.outreach.filters.country
                if config.outreach.filters.size:
                    filters["size"] = config.outreach.filters.size

            # Message template
            if interactive:
                message_template = self.ui.prompt_message_template()
                template_variables = self.ui.prompt_template_variables()
            else:
                if config.outreach.message_template_path:
                    from src.core.tools.message_template import load_template

                    message_template = load_template(
                        config.outreach.message_template_path
                    )
                else:
                    message_template = config.outreach.message_template
                template_variables = {}

            if not message_template:
                self.ui.console.print("No message template provided.", style="red")
                return

            # Preview template
            sample_vars = {
                **template_variables,
                "employee_name": "John Doe",
                "company_name": "Example Co",
                "employee_title": "Software Engineer",
            }
            preview = render_template(message_template, sample_vars)
            self.ui.console.print(
                Panel(preview, title="Message Preview", border_style="cyan")
            )
            self.ui.console.print()

            if interactive and not typer.confirm("Send messages with this template?"):
                self.ui.console.print("Cancelled.", style="yellow")
                return

            # Credentials
            email = config.linkedin.email or os.getenv("LINKEDIN_EMAIL", "")
            password = config.linkedin.password or os.getenv("LINKEDIN_PASSWORD", "")
            if not email or not password:
                self.ui.console.print(
                    "LinkedIn credentials required (config or LINKEDIN_EMAIL/LINKEDIN_PASSWORD env vars)",
                    style="red",
                )
                return

            # Submit to API
            payload = {
                "filters": filters,
                "message_template": message_template,
                "template_variables": template_variables,
                "credentials": {"email": email, "password": password},
                "warm_up": warm_up,
            }

            self.ui.console.print(f"Submitting to {base_url}/api/outreach/run...")

            with httpx.Client(timeout=30) as client:
                resp = client.post(f"{base_url}/api/outreach/run", json=payload)
                resp.raise_for_status()
                task_id = resp.json()["task_id"]

            self.ui.console.print(f"Task submitted: {task_id}\n", style="green")

            if warm_up:
                self.ui.console.print(
                    "Warm-up mode: limiting to 10 messages\n", style="yellow"
                )

            # Consume results from Kafka
            from rich.live import Live
            from rich.spinner import Spinner
            from rich.text import Text

            from src.core.api.schemas.outreach_schemas import OutreachRunResponse
            from src.core.kafka.consumer import KafkaResultConsumer
            from src.core.kafka.producer import TOPIC_OUTREACH_RESULTS

            consumer = KafkaResultConsumer(bootstrap_servers=self._get_kafka_servers())

            with Live(
                Spinner("dots", text="Running outreach workflow..."),
                console=self.ui.console,
            ) as live:
                result = consumer.consume(
                    TOPIC_OUTREACH_RESULTS, task_id, OutreachRunResponse, timeout=600.0
                )
                live.update(Text("Outreach workflow completed!", style="bold green"))

            if result is None:
                self.ui.console.print("Timed out waiting for results.", style="red")
                sys.exit(1)

            final_state = result.model_dump()

            # Display results
            if final_state.get("message_results"):
                self.ui.print_outreach_results(final_state["message_results"])

            if final_state.get("errors"):
                self.ui.print_errors(final_state["errors"])

            self.ui.print_outreach_summary(final_state)
            self._save_results(final_state)

        except KeyboardInterrupt:
            self.ui.console.print("\nOutreach interrupted by user", style="red")
            sys.exit(1)
        except Exception as e:
            if self.ui:
                self.ui.console.print(f"Outreach failed: {str(e)}", style="red")
            logger.exception("Outreach workflow failed")
            sys.exit(1)

    def run(self):
        """Run the CLI application."""
        self.app()

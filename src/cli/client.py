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
from src.core.utils.logging_config import configure_core_agent_logging


class JobApplicationCLI:
    """Command-line interface for the LinkedIn Job Application Agent."""

    # Shared HTTP client with connection pooling
    _http_client: Optional[httpx.Client] = None

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

    @classmethod
    def _get_http_client(cls) -> httpx.Client:
        """Get or create the shared HTTP client with connection pooling."""
        if cls._http_client is None:
            # Long default timeout, can be overridden per-request
            cls._http_client = httpx.Client(
                timeout=httpx.Timeout(30.0, read=600.0),  # 30s connect, 600s read
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return cls._http_client

    @classmethod
    def _close_http_client(cls):
        """Close the shared HTTP client."""
        if cls._http_client is not None:
            cls._http_client.close()
            cls._http_client = None

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
                False, "--warmup/--no-warmup", help="Warm-up mode: cap at 10 messages"
            ),
            total_limit: int = typer.Option(
                None,
                "--total-limit",
                "-tl",
                help="Max total employees to search across all companies",
            ),
        ):
            """Run the employee outreach workflow."""
            self._run_outreach_command(
                config_file or None, interactive, warmup, total_limit
            )

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
        from src.core.agents.tools.company_db import CompanyDB

        self.ui = TerminalUI("rich")
        config = load_config()

        csv_path = csv_path or config.outreach.dataset_path
        db_url = db_path or config.db.company_url

        self.ui.console.print(
            f"Importing [bold]{csv_path}[/bold] into [bold]{db_url}[/bold]..."
        )

        with CompanyDB(db_url) as db:
            total = db.import_csv(
                csv_path,
                on_progress=lambda n: self.ui.console.print(
                    f"  {n:,} rows imported...", end="\r"
                ),
            )
            self.ui.console.print(f"\nImport complete: {total:,} rows", style="green")

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

            client = self._get_http_client()
            resp = client.post(f"{base_url}/api/jobs/apply", json=payload)
            resp.raise_for_status()
            task_id = resp.json()["task_id"]

            self.ui.console.print(f"Task submitted: {task_id}\n", style="green")

            # Consume results from Kafka
            from rich.live import Live
            from rich.spinner import Spinner
            from rich.text import Text

            from src.core.api.schemas.job_schemas import JobApplyResponse
            from src.core.queue.consumer import KafkaResultConsumer
            from src.core.queue.producer import TOPIC_JOB_RESULTS

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
            client = self._get_http_client()
            resp = client.get(f"{base_url}/health", timeout=5.0)
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
        total_limit: Optional[int] = None,
    ):
        """Execute the two-phase outreach workflow: search/cluster → select groups → send."""
        try:
            self.ui = TerminalUI("rich")
            self.ui.start_timer()

            from src.config.config_loader import load_config

            config = load_config(config_file)
            base_url = self._get_api_base_url()

            self.ui.console.print(
                Panel(
                    "LinkedIn Employee Outreach Agent",
                    subtitle="Two-phase outreach: Search → Cluster → Message",
                    border_style="blue",
                )
            )
            self.ui.console.print()

            # Fetch filter options from API
            self.ui.console.print("Loading filter options from API...")
            client = self._get_http_client()
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

                sizes = self._sort_size_intervals(filter_data["sizes"])
                if sizes:
                    selected = self.ui.print_company_filter_menu("size", sizes)
                    if selected:
                        filters["size"] = selected

                # Ask for total employee limit (optional)
                if total_limit is None:
                    limit_input = self.ui.prompt_user_input(
                        "Max total employees to search (leave empty for no limit)"
                    )
                    if limit_input and limit_input.isdigit():
                        total_limit = int(limit_input)

                # Ask for company limit (optional)
                company_limit = None
                company_limit_input = (
                    self.ui.prompt_user_input(
                        "Max companies to search (leave empty for no limit)"
                    )
                    or ""
                )
                if company_limit_input.strip().isdigit():
                    company_limit = int(company_limit_input.strip())

                # Ask for B2C/B2B segment
                segment = None
                segment_input = (
                    (
                        self.ui.prompt_user_input(
                            "Focus on [B2C/B2B/both] (default: both)"
                        )
                        or ""
                    )
                    .strip()
                    .lower()
                )
                if segment_input in ("b2c", "b2b"):
                    segment = segment_input

                # Collect exclusion lists
                exclude_companies = self._collect_exclude_urls("companies")
                exclude_people = self._collect_exclude_urls("people")
            else:
                if config.outreach.filters.industry:
                    filters["industry"] = config.outreach.filters.industry
                if config.outreach.filters.country:
                    filters["country"] = config.outreach.filters.country
                if config.outreach.filters.size:
                    filters["size"] = config.outreach.filters.size
                exclude_companies = []
                exclude_people = []
                segment = None
                company_limit = None

            # Credentials
            email = config.linkedin.email or os.getenv("LINKEDIN_EMAIL", "")
            password = config.linkedin.password or os.getenv("LINKEDIN_PASSWORD", "")
            if not email or not password:
                self.ui.console.print(
                    "LinkedIn credentials required (config or LINKEDIN_EMAIL/LINKEDIN_PASSWORD env vars)",
                    style="red",
                )
                return

            # === Show already-contacted companies and let user choose ===
            client = self._get_http_client()
            if interactive:
                try:
                    resp = client.get(f"{base_url}/api/outreach/contacted-companies")
                    resp.raise_for_status()
                    contacted = resp.json().get("companies", [])

                    if contacted:
                        self.ui.print_contacted_companies(contacted)

                        include_contacted = (
                            self.ui.console.input(
                                "\nInclude already-contacted companies in search? [y/N]: "
                            )
                            .strip()
                            .lower()
                        )

                        if include_contacted != "y":
                            contacted_urls = [
                                c["company_linkedin_url"] for c in contacted
                            ]
                            exclude_companies = list(
                                set(exclude_companies + contacted_urls)
                            )
                            self.ui.console.print(
                                f"[dim]Excluding {len(contacted_urls)} already-contacted companies[/dim]\n"
                            )
                except Exception as e:
                    self.ui.console.print(
                        f"[dim]Could not fetch contacted companies: {e}[/dim]"
                    )

            # === PHASE 1: Search & Cluster ===
            self.ui.console.print(
                "\n[bold cyan]Phase 1: Searching employees and clustering by role...[/bold cyan]\n"
            )

            search_payload = {
                "filters": filters,
                "credentials": {"email": email, "password": password},
            }
            if total_limit is not None:
                search_payload["total_limit"] = total_limit
                self.ui.console.print(
                    f"Total employee limit: [bold yellow]{total_limit}[/bold yellow]\n"
                )
            if company_limit is not None:
                search_payload["company_limit"] = company_limit
                self.ui.console.print(
                    f"Company limit: [bold yellow]{company_limit}[/bold yellow]\n"
                )
            if segment:
                search_payload["segment"] = segment
                self.ui.console.print(
                    f"Segment: [bold yellow]{segment.upper()}[/bold yellow]\n"
                )
            if exclude_companies:
                search_payload["exclude_companies"] = exclude_companies
                self.ui.console.print(
                    f"Excluding [bold yellow]{len(exclude_companies)}[/bold yellow] companies\n"
                )
            if exclude_people:
                search_payload["exclude_profile_urls"] = exclude_people
                self.ui.console.print(
                    f"Excluding [bold yellow]{len(exclude_people)}[/bold yellow] people\n"
                )

            import time as _time

            from rich.live import Live
            from rich.spinner import Spinner
            from rich.text import Text

            # Submit search (returns immediately with task_id)
            t_submit = _time.perf_counter()
            client = self._get_http_client()
            resp = client.post(f"{base_url}/api/outreach/search", json=search_payload)
            resp.raise_for_status()
            search_task_id = resp.json()["task_id"]
            t_post_submit = _time.perf_counter()
            self.ui.console.print(
                f"[dim][TIMING] Task submitted in {round((t_post_submit - t_submit) * 1000, 2)}ms[/dim]"
            )

            # Poll Kafka for search results
            from src.core.api.schemas.outreach_schemas import OutreachSearchResponse
            from src.core.queue.consumer import KafkaResultConsumer
            from src.core.queue.producer import TOPIC_OUTREACH_SEARCH_RESULTS

            consumer = KafkaResultConsumer(
                bootstrap_servers=self._get_kafka_servers(),
            )

            from rich.status import Status

            t_pre_consume = _time.perf_counter()

            # Simple spinner with elapsed time - no fake progress
            with Status(
                "Searching employees and clustering by role...",
                console=self.ui.console,
                spinner="dots",
            ) as status:
                search_result_msg = consumer.consume(
                    TOPIC_OUTREACH_SEARCH_RESULTS,
                    search_task_id,
                    OutreachSearchResponse,
                    timeout=3600.0,
                )

            t_post_consume = _time.perf_counter()
            elapsed_sec = round(t_post_consume - t_pre_consume, 1)
            self.ui.console.print(
                f"[bold green]Search complete![/bold green] [dim]({elapsed_sec}s)[/dim]"
            )

            self.ui.console.print(
                f"[dim][TIMING] Kafka consume took {round((t_post_consume - t_pre_consume) * 1000, 2)}ms[/dim]"
            )
            self.ui.console.print(
                f"[dim][TIMING] Total wait from submit: {round((t_post_consume - t_submit) * 1000, 2)}ms[/dim]"
            )

            if search_result_msg is None:
                self.ui.console.print(
                    "Timed out waiting for search results.", style="red"
                )
                return

            session_id = search_result_msg.session_id
            role_groups = search_result_msg.role_groups
            total_employees = search_result_msg.total_employees
            companies_processed = search_result_msg.companies_processed

            if not session_id or total_employees == 0:
                self.ui.console.print(
                    "No employees found matching filters.", style="yellow"
                )
                return

            self.ui.console.print(
                f"\nFound [bold green]{total_employees}[/bold green] employees "
                f"across [bold green]{companies_processed}[/bold green] companies\n"
            )

            # Display role groups
            self.ui.print_role_groups(role_groups)

            # Let user fix LLM misclassifications before proceeding
            reassignments = {}
            if interactive:
                role_groups, reassignments = self.ui.prompt_role_reassignment(
                    role_groups
                )

            # === Select Role Groups ===
            if interactive:
                selected_roles = self.ui.prompt_group_selection(role_groups)
            else:
                # Non-interactive: select all non-empty groups
                selected_roles = [role for role, emps in role_groups.items() if emps]

            if not selected_roles:
                self.ui.console.print("No role groups selected.", style="yellow")
                return

            self.ui.console.print(
                f"\nSelected groups: [bold cyan]{', '.join(selected_roles)}[/bold cyan]\n"
            )

            # === Show company distribution and recipient selection options ===
            max_per_company = None
            selected_employee_urls: set[str] | None = None  # None = all, set = specific

            if interactive:
                # Build flat list of employees in selected roles with company info
                all_employees_in_selection: list[dict] = []
                for role in selected_roles:
                    for emp in role_groups.get(role, []):
                        all_employees_in_selection.append({**emp, "_role": role})

                # Calculate employees per company
                company_counts: dict[str, int] = {}
                company_employees: dict[str, list[dict]] = {}
                for emp in all_employees_in_selection:
                    company = emp.get("company_name", "Unknown")
                    company_counts[company] = company_counts.get(company, 0) + 1
                    if company not in company_employees:
                        company_employees[company] = []
                    company_employees[company].append(emp)

                # Show top companies with most employees
                sorted_companies = sorted(
                    company_counts.items(), key=lambda x: x[1], reverse=True
                )
                if sorted_companies:
                    self.ui.console.print(
                        "\n[bold]Employees per company (top 10):[/bold]"
                    )
                    for company, count in sorted_companies[:10]:
                        self.ui.console.print(f"  {company}: {count}")
                    if len(sorted_companies) > 10:
                        self.ui.console.print(
                            f"  ... and {len(sorted_companies) - 10} more companies"
                        )

                # Selection menu
                self.ui.console.print(
                    "\n[bold]How do you want to select recipients?[/bold]"
                )
                self.ui.console.print("  1. Send to all employees in selected groups")
                self.ui.console.print("  2. Set max per company limit")
                self.ui.console.print("  3. Select specific employees")

                selection_choice = (
                    self.ui.console.input("\nChoice [1]: ").strip() or "1"
                )

                if selection_choice == "2":
                    # Max per company
                    max_per_company_input = self.ui.console.input(
                        "Max messages per company: "
                    ).strip()
                    if max_per_company_input:
                        try:
                            max_per_company = int(max_per_company_input)
                            if max_per_company < 1:
                                max_per_company = None
                        except ValueError:
                            pass

                    if max_per_company:
                        limited_total = sum(
                            min(count, max_per_company)
                            for count in company_counts.values()
                        )
                        self.ui.console.print(
                            f"\nLimiting to [bold yellow]{max_per_company}[/bold yellow] per company "
                            f"(~{limited_total} messages instead of {sum(company_counts.values())})"
                        )

                elif selection_choice == "3":
                    # Select specific employees
                    selected_employee_urls = set()

                    self.ui.console.print("\n[bold]Select employees by company:[/bold]")
                    self.ui.console.print(
                        "For each company, enter employee numbers to include (comma-separated)"
                    )
                    self.ui.console.print(
                        "Press Enter to skip company, 'all' to include all, 'q' to finish\n"
                    )

                    for company in sorted(company_employees.keys()):
                        emps = company_employees[company]
                        self.ui.console.print(
                            f"\n[bold cyan]{company}[/bold cyan] ({len(emps)} employees):"
                        )

                        for i, emp in enumerate(emps, 1):
                            role = emp.get("_role", "")
                            self.ui.console.print(
                                f"  {i}. {emp.get('name', 'Unknown')} - {emp.get('title', 'N/A')} [{role}]"
                            )

                        choice = (
                            self.ui.console.input(
                                "Include (e.g. 1,2,3 or 'all' or Enter to skip): "
                            )
                            .strip()
                            .lower()
                        )

                        if choice == "q":
                            break
                        elif choice == "all":
                            for emp in emps:
                                url = emp.get("profile_url", "")
                                if url:
                                    selected_employee_urls.add(url)
                        elif choice:
                            try:
                                indices = [int(x.strip()) for x in choice.split(",")]
                                for idx in indices:
                                    if 1 <= idx <= len(emps):
                                        url = emps[idx - 1].get("profile_url", "")
                                        if url:
                                            selected_employee_urls.add(url)
                            except ValueError:
                                self.ui.console.print(
                                    "Invalid input, skipping company", style="yellow"
                                )

                    if selected_employee_urls:
                        self.ui.console.print(
                            f"\n[bold green]Selected {len(selected_employee_urls)} employees[/bold green]"
                        )
                    else:
                        self.ui.console.print(
                            "\nNo employees selected.", style="yellow"
                        )
                        return

            # === Prompt Templates Per Role Group ===
            selected_groups_config = {}

            # Load per-role templates from JSON if available
            role_templates = {}
            if config.outreach.role_templates_path:
                role_templates_file = Path(config.outreach.role_templates_path)
                if role_templates_file.exists():
                    role_templates = json.loads(role_templates_file.read_text("utf-8"))
                    self.ui.console.print(
                        f"Loaded role templates for: {', '.join(role_templates.keys())}",
                        style="dim",
                    )

            # Load fallback default template
            default_template = None
            if config.outreach.message_template_path:
                from src.core.agents.tools.message_template import load_template

                default_template = load_template(config.outreach.message_template_path)
            elif config.outreach.message_template:
                default_template = config.outreach.message_template

            for role in selected_roles:
                employees_in_role = role_groups.get(role, [])
                count = len(employees_in_role)
                sample_employee = employees_in_role[0] if employees_in_role else None

                # Use role-specific template if available, otherwise fallback
                role_default = None
                if role in role_templates:
                    tpl = role_templates[role]
                    role_default = (
                        tpl if isinstance(tpl, str) else tpl.get("message", "")
                    )
                if not role_default:
                    role_default = default_template

                if interactive:
                    template, variables = self.ui.prompt_template_for_role(
                        role, count, role_default
                    )

                    # Preview-edit-confirm loop
                    while True:
                        result = self.ui.print_message_preview(
                            role, template, variables, sample_employee
                        )
                        if result == "confirm":
                            break
                        elif result == "edit":
                            template = self.ui.edit_in_editor(
                                template,
                                header_comment=(
                                    f"Editing template for: {role}\n\n"
                                    "Available placeholders:\n"
                                    "  {employee_name}  - Full name\n"
                                    "  {first_name}     - First name only\n"
                                    "  {company_name}   - Company name\n"
                                    "  {employee_title} - Job title\n"
                                    "  {my_name}        - Your name\n"
                                    "  {my_role}        - Your role/title\n"
                                    "  {topic}          - Topic/reason for outreach\n"
                                    "  {custom_closing} - Custom closing"
                                ),
                            )
                        else:
                            # reject: re-enter from scratch
                            template, variables = self.ui.prompt_template_for_role(
                                role, count, role_default
                            )
                else:
                    # Non-interactive: use role template or fallback
                    if not role_default:
                        self.ui.console.print(
                            f"No message template for role '{role}'.", style="red"
                        )
                        return
                    template = role_default
                    variables = {}

                selected_groups_config[role] = {
                    "enabled": True,
                    "message_template": template,
                    "template_variables": variables,
                }

            # Review all templates before sending
            if interactive:
                selected_groups_config = self.ui.review_all_templates(
                    selected_groups_config, role_groups
                )

            # Final confirmation
            total_to_send = sum(
                len(role_groups.get(role, [])) for role in selected_roles
            )

            if interactive:
                if selected_employee_urls:
                    confirm_msg = f"\nSend messages to {len(selected_employee_urls)} selected employees?"
                elif max_per_company:
                    confirm_msg = f"\nSend messages (max {max_per_company}/company) to {len(selected_roles)} groups?"
                else:
                    confirm_msg = f"\nSend messages to {total_to_send} employees in {len(selected_roles)} groups?"

                if not typer.confirm(confirm_msg):
                    self.ui.console.print("Cancelled.", style="yellow")
                    return

            # === PHASE 2: Send Messages ===
            self.ui.console.print(
                "\n[bold cyan]Phase 2: Sending messages...[/bold cyan]\n"
            )

            send_payload = {
                "session_id": session_id,
                "selected_groups": selected_groups_config,
                "credentials": {"email": email, "password": password},
                "warm_up": warm_up,
            }
            if max_per_company:
                send_payload["max_per_company"] = max_per_company
            if selected_employee_urls:
                send_payload["selected_employees"] = list(selected_employee_urls)
            if reassignments:
                send_payload["reassignments"] = reassignments

            client = self._get_http_client()
            resp = client.post(f"{base_url}/api/outreach/send", json=send_payload)
            resp.raise_for_status()
            task_id = resp.json()["task_id"]

            self.ui.console.print(f"Task submitted: {task_id}", style="green")

            if warm_up:
                self.ui.console.print(
                    "Warm-up mode: limiting to 10 messages\n", style="yellow"
                )

            # Consume results from Kafka
            from src.core.api.schemas.outreach_schemas import OutreachSendResponse
            from src.core.queue.consumer import KafkaResultConsumer
            from src.core.queue.producer import TOPIC_OUTREACH_RESULTS

            consumer = KafkaResultConsumer(
                bootstrap_servers=self._get_kafka_servers(),
            )

            with Live(
                Spinner("dots", text="Sending messages..."),
                console=self.ui.console,
            ) as live:
                result = consumer.consume(
                    TOPIC_OUTREACH_RESULTS, task_id, OutreachSendResponse, timeout=600.0
                )
                live.update(Text("Message sending complete!", style="bold green"))

            if result is None:
                self.ui.console.print("Timed out waiting for results.", style="red")
                sys.exit(1)

            final_state = result.model_dump()

            # Display results by role
            self.ui.print_outreach_results_by_role(
                final_state.get("message_results", []),
                final_state.get("results_by_role", {}),
            )

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

    def _collect_exclude_urls(self, label: str) -> List[str]:
        """Collect LinkedIn URLs to exclude, either inline or from a .txt file.

        User can type URLs one per line (empty line to finish),
        or provide a path to a .txt file with one URL per line.
        """
        self.ui.console.print(
            f"\nExclude {label} by LinkedIn URL "
            "(enter URLs one per line, empty to finish, or path to .txt file):"
        )
        first_line = (self.ui.prompt_user_input("URL or .txt path") or "").strip()

        if not first_line:
            return []

        # Check if it's a file path
        if first_line.endswith(".txt") and os.path.isfile(first_line):
            with open(first_line) as f:
                urls = [line.strip() for line in f if line.strip()]
            self.ui.console.print(
                f"Loaded {len(urls)} URLs from {first_line}", style="green"
            )
            return urls

        # Inline entry: first line is a URL, keep reading until empty
        urls = [first_line]
        while True:
            line = (self.ui.prompt_user_input("URL (empty to finish)") or "").strip()
            if not line:
                break
            urls.append(line)

        return urls

    @staticmethod
    def _sort_size_intervals(sizes: List[str]) -> List[str]:
        """Sort company size intervals by their lower bound numerically.

        Handles formats like "1-10", "11-50", "51-200", "10001+", "Self-employed".
        """
        import re

        def sort_key(s: str) -> int:
            match = re.match(r"(\d+)", s)
            if match:
                return int(match.group(1))
            return float("inf")  # Non-numeric values go last

        return sorted(sizes, key=sort_key)

    def run(self):
        """Run the CLI application."""
        self.app()

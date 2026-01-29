"""Main CLI client for the LinkedIn Job Application Agent."""

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.panel import Panel

from cli.config import CLIConfig, JobSearchConfig
from cli.ui import TerminalUI
from src.core.agent import JobApplicationAgent
from src.core.utils.logging_config import (
    configure_core_agent_logging,
    get_core_agent_logger,
    log_core_agent_completion,
    log_core_agent_startup,
)


class JobApplicationCLI:
    """Command-line interface for the LinkedIn Job Application Agent."""

    def __init__(self):
        # Load .env file if it exists
        load_dotenv()

        # Configure core agent logging
        configure_core_agent_logging()

        self.app = typer.Typer(
            name="job-applier",
            help="LinkedIn Job Application Agent - Automated job search and application system",
            no_args_is_help=True,
            rich_markup_mode=None,  # Disable rich formatting
        )
        self.ui = None
        self.config = None

        # Register commands
        self._register_commands()

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
            """Test connection to MCP server."""
            self._test_connection_command("localhost", 3000)

        @self.app.command("outreach")
        def outreach(
            config_file: str = typer.Option(
                "", "--config", "-c", help="Path to agent config YAML"
            ),
            interactive: bool = typer.Option(
                True, help="Interactive mode"
            ),
            warm_up: bool = typer.Option(
                False, help="Warm-up mode: cap at 10 messages"
            ),
        ):
            """Run the employee outreach workflow."""
            self._run_outreach_command(
                config_file or None, interactive, warm_up
            )

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
        """Execute the run workflow command."""
        try:
            # Initialize UI
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

            # Always ask for job searches if none are configured
            if not self.config.job_searches:
                self._interactive_job_search_setup()

            # Validate configuration
            missing_fields = self.config.validate_required_fields()
            if missing_fields:
                self.ui.console.print(
                    f"❌ Missing required configuration: {', '.join(missing_fields)}",
                    style="red",
                )
                self.ui.console.print(
                    "Use 'job-applier init' to create a configuration file or set environment variables."
                )
                sys.exit(1)

            # Show configuration summary
            self.ui.print_config_summary(self.config)
            self.ui.print_job_searches(self.config.job_searches)

            # Setup logging
            self._setup_logging()

            # Run the workflow
            self._execute_workflow()

        except KeyboardInterrupt:
            self.ui.console.print("\\n❌ Workflow interrupted by user", style="red")
            sys.exit(1)
        except Exception as e:
            self.ui.console.print(f"❌ Workflow failed: {str(e)}", style="red")
            logger.exception("Workflow execution failed")
            sys.exit(1)

    def _init_config_command(self, config_file: Optional[str], interactive: bool):
        """Execute the init config command."""
        self.ui = TerminalUI("rich")

        if not config_file:
            config_file = CLIConfig().get_default_config_path()

        # Check if config file already exists
        if os.path.exists(config_file):
            overwrite = typer.confirm(
                f"Configuration file {config_file} already exists. Overwrite?"
            )
            if not overwrite:
                self.ui.console.print("❌ Configuration initialization cancelled")
                return

        # Create new configuration
        if interactive:
            config = self._create_interactive_config()
        else:
            config = self._create_default_config()

        # Save configuration
        config.save_to_file(config_file)
        self.ui.console.print(f"✅ Configuration saved to {config_file}", style="green")
        self.ui.console.print("Edit the file to customize your job search criteria.")

    def _validate_config_command(self, config_file: Optional[str]):
        """Execute the validate config command."""
        self.ui = TerminalUI("rich")

        if not config_file:
            config_file = CLIConfig().get_default_config_path()

        try:
            config = CLIConfig.load_from_file(config_file)
            # Merge with environment variables
            config = config.merge_with_env()
            missing_fields = config.validate_required_fields()

            if missing_fields:
                self.ui.console.print(
                    f"❌ Configuration validation failed:", style="red"
                )
                for field in missing_fields:
                    self.ui.console.print(f"  - Missing: {field}", style="red")
            else:
                self.ui.console.print("✅ Configuration is valid", style="green")
                self.ui.print_config_summary(config)

        except Exception as e:
            self.ui.console.print(
                f"❌ Configuration validation failed: {str(e)}", style="red"
            )

    def _test_connection_command(self, mcp_host: str, mcp_port: int):
        """Execute the test connection command."""
        self.ui = TerminalUI("rich")

        self.ui.console.print(
            f"Testing connection to MCP server at {mcp_host}:{mcp_port}..."
        )

        try:
            # Try to create agent and test connection
            agent = JobApplicationAgent(server_host=mcp_host, server_port=mcp_port)
            self.ui.console.print("✅ Connection successful", style="green")

        except Exception as e:
            self.ui.console.print(f"❌ Connection failed: {str(e)}", style="red")
            self.ui.console.print("Make sure the MCP server is running and accessible.")

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

        # Start with defaults
        config = CLIConfig(
            mcp_server_host=mcp_host,
            mcp_server_port=mcp_port,
            output_format=output_format,
            save_results=save_results if save_results is not None else True,
        )

        # Load from config file if provided, or try to find default
        if not config_file:
            # Try to find a default config file
            default_config = CLIConfig().get_default_config_path()
            if os.path.exists(default_config):
                config_file = default_config

        if config_file and os.path.exists(config_file):
            file_config = CLIConfig.load_from_file(config_file)
            # Merge file config with defaults
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
                f"⚠️  Configuration file {config_file} not found, using defaults",
                style="yellow",
            )

        # Override with environment variables
        config = config.merge_with_env()

        # Override with command line arguments
        if linkedin_email:
            config.linkedin_email = linkedin_email
        if linkedin_password:
            config.linkedin_password = linkedin_password
        if cv_file:
            config.cv_file_path = cv_file

        return config

    def _interactive_job_search_setup(self):
        """Interactive setup for job search criteria."""
        self.ui.console.print("🔧 Interactive Job Search Setup", style="bold blue")

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
                    f"✅ Added job search: {job_title} in {location}", style="green"
                )

                if not typer.confirm("Add another job search?"):
                    break

            except ValueError as e:
                self.ui.console.print(f"❌ Invalid input: {str(e)}", style="red")

        self.config.job_searches = job_searches

    def _create_interactive_config(self) -> CLIConfig:
        """Create configuration interactively."""
        self.ui.console.print("🔧 Interactive Configuration Setup", style="bold blue")

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

        # Add job searches
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

    def _setup_logging(self):
        """Setup logging configuration using core agent logging to maintain trace_id consistency."""
        from src.core.utils.logging_config import configure_core_agent_logging

        # Use core agent logging configuration which supports trace_id
        configure_core_agent_logging(
            log_level=self.config.log_level, log_file=self.config.log_file
        )

    def _execute_workflow(self):
        """Execute the main job application workflow."""
        try:
            # Initialize the agent
            agent = JobApplicationAgent(
                server_host=self.config.mcp_server_host,
                server_port=self.config.mcp_server_port,
            )

            # Prepare job search requests
            job_search_requests = [
                {
                    "job_title": search.job_title,
                    "location": search.location,
                    "monthly_salary": search.monthly_salary,
                    "limit": search.limit,
                }
                for search in self.config.job_searches
            ]

            # Prepare user credentials
            user_credentials = {
                "email": self.config.linkedin_email,
                "password": self.config.linkedin_password,
            }

            # Use logger that will have trace_id after agent.run() configures it
            # We'll bind a temporary trace_id for the initial log
            import uuid

            from src.core.utils.logging_config import get_core_agent_logger

            temp_trace_id = str(uuid.uuid4())
            logger = get_core_agent_logger(temp_trace_id)
            logger.info("Starting job application workflow")

            # Run the workflow with progress updates
            if self.config.output_format == "rich":
                self._run_workflow_with_progress(
                    agent, job_search_requests, user_credentials
                )
            else:
                final_state = agent.run(
                    job_searches=job_search_requests,
                    cv_file_path=self.config.cv_file_path,
                    user_credentials=user_credentials,
                )
                self._handle_workflow_results(final_state)

        except Exception as e:
            import uuid

            from src.core.utils.logging_config import get_core_agent_logger

            temp_trace_id = str(uuid.uuid4())
            logger = get_core_agent_logger(temp_trace_id)
            logger.exception("Workflow execution failed")
            raise

    def _run_workflow_with_progress(self, agent, job_search_requests, user_credentials):
        """Run workflow with rich progress display."""
        from rich.live import Live
        from rich.spinner import Spinner
        from rich.text import Text

        # This is a simplified version - in a real implementation,
        # you'd want to modify the agent to provide progress callbacks
        with Live(
            Spinner("dots", text="Starting workflow..."), console=self.ui.console
        ) as live:
            final_state = agent.run(
                job_searches=job_search_requests,
                user_credentials=user_credentials,
                cv_data_path=self.config.cv_file_path,  # Now expects CV JSON data path
            )

            live.update(Text("✅ Workflow completed!", style="bold green"))

        self._handle_workflow_results(final_state)

    def _handle_workflow_results(self, final_state: Dict[str, Any]):
        """Handle and display workflow results."""
        # Display CV analysis
        if final_state.get("cv_analysis"):
            self.ui.print_cv_analysis(final_state["cv_analysis"])

        # Display job results
        if final_state.get("all_found_jobs"):
            self.ui.print_job_results(final_state["all_found_jobs"])

        # Display application results
        if final_state.get("application_results"):
            self.ui.print_application_results(final_state["application_results"])

        # Display errors
        if final_state.get("errors"):
            self.ui.print_errors(final_state["errors"])

        # Display final summary
        self.ui.print_final_summary(final_state)

        # Save results if configured
        if self.config.save_results:
            self._save_results(final_state)

        # Use trace_id-aware logger, getting trace_id from final_state
        trace_id = final_state.get("trace_id", "unknown")
        from src.core.utils.logging_config import get_core_agent_logger

        logger_with_trace = get_core_agent_logger(trace_id)
        logger_with_trace.info("Workflow completed successfully")

    def _save_results(self, final_state: Dict[str, Any]):
        """Save workflow results to file."""
        # Initialize logger outside try block to ensure it's available in except
        save_logger = None
        try:
            # Use bound logger for save operations
            save_logger = get_core_agent_logger("save-results")
            # Create results directory
            results_dir = Path(self.config.results_directory)
            results_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"job_application_results_{timestamp}.json"
            filepath = results_dir / filename

            # Clean up state for JSON serialization
            clean_state = {
                k: v for k, v in final_state.items() if k not in ["cv_content"]
            }

            # Save to file
            with open(filepath, "w") as f:
                json.dump(clean_state, f, indent=2, default=str)

            self.ui.console.print(f"📁 Results saved to {filepath}", style="blue")

        except Exception as e:
            if save_logger:
                save_logger.warning(f"Failed to save results: {str(e)}")
            else:
                self.ui.console.print(f"❌ Failed to save results: {str(e)}", style="red")
            self.ui.console.print(
                f"⚠️  Failed to save results: {str(e)}", style="yellow"
            )

    def _run_outreach_command(
        self,
        config_file: Optional[str],
        interactive: bool,
        warm_up: bool,
    ):
        """Execute the outreach workflow command."""
        from src.config.config_loader import load_config
        from src.core.agents.outreach_agent import EmployeeOutreachAgent
        from src.core.tools.company_loader import (
            filter_companies,
            get_unique_values,
            load_companies,
        )
        from src.core.tools.message_template import render_template

        try:
            self.ui = TerminalUI("rich")
            self.ui.start_timer()

            # Load central config
            config = load_config(config_file)

            self.ui.console.print(
                Panel(
                    "LinkedIn Employee Outreach Agent",
                    subtitle="Automated employee messaging system",
                    border_style="blue",
                )
            )
            self.ui.console.print()

            # Load company dataset
            dataset_path = config.outreach.dataset_path
            self.ui.console.print(f"Loading dataset from {dataset_path}...")
            df = load_companies(dataset_path)
            total_count = len(df)
            self.ui.console.print(
                f"Loaded [bold green]{total_count}[/bold green] companies\n"
            )

            # Interactive filtering
            filters = {}
            if interactive:
                # Industry filter
                industries = get_unique_values(df, "industry")
                if industries:
                    selected = self.ui.print_company_filter_menu("industry", industries)
                    if selected:
                        filters["industry"] = selected

                # Country filter
                countries = get_unique_values(df, "country")
                if countries:
                    selected = self.ui.print_company_filter_menu("country", countries)
                    if selected:
                        filters["country"] = selected

                # Size filter
                sizes = get_unique_values(df, "size")
                if sizes:
                    selected = self.ui.print_company_filter_menu("size", sizes)
                    if selected:
                        filters["size"] = selected
            else:
                # Use filters from config
                if config.outreach.filters.industry:
                    filters["industry"] = config.outreach.filters.industry
                if config.outreach.filters.country:
                    filters["country"] = config.outreach.filters.country
                if config.outreach.filters.size:
                    filters["size"] = config.outreach.filters.size

            # Apply filters
            filtered_df = filter_companies(df, filters)
            companies = filtered_df.to_dict("records")

            # Show summary
            self.ui.print_filtered_companies_summary(companies, total_count)

            if not companies:
                self.ui.console.print("No companies match the filters.", style="red")
                return

            # Confirm
            if interactive and not typer.confirm("Proceed with these companies?"):
                self.ui.console.print("Cancelled.", style="yellow")
                return

            # Message template
            if interactive:
                message_template = self.ui.prompt_message_template()
                template_variables = self.ui.prompt_template_variables()
            else:
                # Load from config
                if config.outreach.message_template_path:
                    from src.core.tools.message_template import load_template
                    message_template = load_template(config.outreach.message_template_path)
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
                "company_name": companies[0].get("name", "Example Co"),
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

            user_credentials = {"email": email, "password": password}

            # Override daily limit for warm-up
            if warm_up:
                config.outreach.daily_message_limit = 10
                self.ui.console.print(
                    "Warm-up mode: limiting to 10 messages\n", style="yellow"
                )

            # Run the outreach agent
            agent = EmployeeOutreachAgent(config_file)

            from rich.live import Live
            from rich.spinner import Spinner
            from rich.text import Text

            with Live(
                Spinner("dots", text="Running outreach workflow..."),
                console=self.ui.console,
            ) as live:
                final_state = agent.run(
                    companies=companies,
                    message_template=message_template,
                    template_variables=template_variables,
                    user_credentials=user_credentials,
                )
                live.update(Text("Outreach workflow completed!", style="bold green"))

            # Display results
            if final_state.get("message_results"):
                self.ui.print_outreach_results(final_state["message_results"])

            if final_state.get("errors"):
                self.ui.print_errors(final_state["errors"])

            self.ui.print_outreach_summary(final_state)

            # Save results
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

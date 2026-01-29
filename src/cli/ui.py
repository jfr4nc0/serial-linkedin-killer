"""Rich terminal UI components for the CLI client."""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree


class TerminalUI:
    """Rich terminal UI for the job application workflow."""

    def __init__(self, output_format: str = "rich"):
        self.console = Console()
        self.output_format = output_format
        self.start_time = None

    def print_header(self):
        """Print application header."""
        if self.output_format != "rich":
            return

        header_text = Text("LinkedIn Job Application Agent", style="bold blue")
        header_text.append(" 🤖", style="bold yellow")

        panel = Panel(
            header_text,
            subtitle="Automated job search and application system",
            border_style="blue",
        )
        self.console.print(panel)
        self.console.print()

    def print_config_summary(self, config):
        """Print configuration summary."""
        if self.output_format == "json":
            return

        table = Table(
            title="Configuration Summary", show_header=True, header_style="bold magenta"
        )
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row(
            "MCP Server", f"{config.mcp_server_host}:{config.mcp_server_port}"
        )
        table.add_row("CV Data", config.cv_file_path)
        table.add_row("LinkedIn Email", config.linkedin_email)
        table.add_row("Job Searches", str(len(config.job_searches)))

        if self.output_format == "rich":
            self.console.print(table)
        else:
            # Simple format
            self.console.print("Configuration:")
            self.console.print(
                f"  MCP Server: {config.mcp_server_host}:{config.mcp_server_port}"
            )
            self.console.print(f"  CV File: {config.cv_file_path}")
            self.console.print(f"  Job Searches: {len(config.job_searches)}")

        self.console.print()

    def print_job_searches(self, job_searches: List[Dict]):
        """Print job search configurations."""
        if self.output_format == "json":
            return

        table = Table(
            title="Job Search Criteria", show_header=True, header_style="bold magenta"
        )
        table.add_column("Job Title", style="cyan")
        table.add_column("Location", style="green")
        table.add_column("Salary", style="yellow")
        table.add_column("Limit", style="blue")

        for search in job_searches:
            table.add_row(
                search.job_title,
                search.location,
                f"${search.monthly_salary:,}/month",
                str(search.limit),
            )

        if self.output_format == "rich":
            self.console.print(table)
        else:
            self.console.print("Job Search Criteria:")
            for i, search in enumerate(job_searches, 1):
                self.console.print(
                    f"  {i}. {search.job_title} in {search.location} (${search.monthly_salary:,}/month, limit: {search.limit})"
                )

        self.console.print()

    def create_progress_display(self) -> Progress:
        """Create a progress display for the workflow."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def show_workflow_progress(self, agent_state: Dict[str, Any]):
        """Show live workflow progress."""
        if self.output_format != "rich":
            # Simple text output
            self.console.print(
                f"Status: {agent_state.get('current_status', 'Unknown')}"
            )
            return

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="status", size=3),
            Layout(name="details"),
        )

        # Status panel
        status = agent_state.get("current_status", "Starting...")
        status_panel = Panel(
            Text(status, style="bold green"),
            title="Current Status",
            border_style="green",
        )
        layout["status"].update(status_panel)

        # Details panel
        details_text = Text()

        if agent_state.get("total_jobs_found"):
            details_text.append(
                f"📍 Jobs Found: {agent_state['total_jobs_found']}\n", style="blue"
            )

        if agent_state.get("filtered_jobs"):
            details_text.append(
                f"✅ Jobs Filtered: {len(agent_state['filtered_jobs'])}\n",
                style="green",
            )

        if agent_state.get("total_jobs_applied"):
            details_text.append(
                f"🎯 Applications Submitted: {agent_state['total_jobs_applied']}\n",
                style="yellow",
            )

        if agent_state.get("errors"):
            details_text.append(
                f"❌ Errors: {len(agent_state['errors'])}\n", style="red"
            )

        details_panel = Panel(
            details_text, title="Progress Details", border_style="blue"
        )
        layout["details"].update(details_panel)

        self.console.print(layout)

    def print_cv_analysis(self, cv_analysis: Dict[str, Any]):
        """Print CV analysis results."""
        if self.output_format == "json":
            print(json.dumps({"cv_analysis": cv_analysis}, indent=2))
            return

        tree = Tree("📄 CV Analysis", style="bold blue")

        # Experience
        exp_branch = tree.add("💼 Experience", style="green")
        exp_branch.add(f"Years: {cv_analysis.get('experience_years', 0)}")

        # Skills
        skills_branch = tree.add("🛠️  Skills", style="cyan")
        skills = cv_analysis.get("skills", [])
        for skill in skills[:10]:  # Show first 10 skills
            skills_branch.add(skill)
        if len(skills) > 10:
            skills_branch.add(f"... and {len(skills) - 10} more")

        # Previous roles
        roles_branch = tree.add("👔 Previous Roles", style="yellow")
        roles = cv_analysis.get("previous_roles", [])
        for role in roles[:5]:  # Show first 5 roles
            roles_branch.add(role)
        if len(roles) > 5:
            roles_branch.add(f"... and {len(roles) - 5} more")

        # Technologies
        tech_branch = tree.add("💻 Technologies", style="magenta")
        technologies = cv_analysis.get("technologies", [])
        for tech in technologies[:8]:  # Show first 8 technologies
            tech_branch.add(tech)
        if len(technologies) > 8:
            tech_branch.add(f"... and {len(technologies) - 8} more")

        if self.output_format == "rich":
            self.console.print(tree)
        else:
            self.console.print("CV Analysis:")
            self.console.print(
                f"  Experience: {cv_analysis.get('experience_years', 0)} years"
            )
            self.console.print(
                f"  Skills: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}"
            )
            self.console.print(
                f"  Previous Roles: {', '.join(roles[:3])}{'...' if len(roles) > 3 else ''}"
            )

        self.console.print()

    def print_job_results(self, jobs: List[Dict[str, Any]]):
        """Print job search results."""
        if self.output_format == "json":
            print(json.dumps({"jobs_found": jobs}, indent=2))
            return

        if not jobs:
            self.console.print("❌ No jobs found", style="red")
            return

        table = Table(
            title=f"Found {len(jobs)} Jobs",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Job ID", style="cyan")
        table.add_column("Description Preview", style="green", max_width=60)

        for job in jobs:
            description_preview = (
                job.get("job_description", "")[:100] + "..."
                if len(job.get("job_description", "")) > 100
                else job.get("job_description", "")
            )
            table.add_row(str(job.get("id_job", "N/A")), description_preview)

        if self.output_format == "rich":
            self.console.print(table)
        else:
            self.console.print(f"Found {len(jobs)} jobs:")
            for i, job in enumerate(jobs, 1):
                description_preview = (
                    job.get("job_description", "")[:50] + "..."
                    if len(job.get("job_description", "")) > 50
                    else job.get("job_description", "")
                )
                self.console.print(
                    f"  {i}. Job {job.get('id_job')}: {description_preview}"
                )

        self.console.print()

    def print_application_results(self, application_results: List[Dict[str, Any]]):
        """Print job application results."""
        if self.output_format == "json":
            print(json.dumps({"application_results": application_results}, indent=2))
            return

        if not application_results:
            self.console.print("❌ No applications submitted", style="red")
            return

        table = Table(
            title="Application Results", show_header=True, header_style="bold magenta"
        )
        table.add_column("Job ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Error", style="red")

        successful = 0
        for result in application_results:
            status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
            error = result.get("error", "") if not result.get("success") else ""

            table.add_row(
                str(result.get("id_job", "N/A")),
                status,
                error[:50] + "..." if len(error) > 50 else error,
            )

            if result.get("success"):
                successful += 1

        if self.output_format == "rich":
            self.console.print(table)
        else:
            self.console.print(
                f"Application Results ({successful}/{len(application_results)} successful):"
            )
            for result in application_results:
                status = "SUCCESS" if result.get("success") else "FAILED"
                self.console.print(f"  Job {result.get('id_job')}: {status}")
                if not result.get("success") and result.get("error"):
                    self.console.print(f"    Error: {result['error'][:100]}")

        self.console.print()

    def print_final_summary(self, final_state: Dict[str, Any]):
        """Print final workflow summary."""
        if self.output_format == "json":
            # Clean up the state for JSON output
            clean_state = {
                k: v for k, v in final_state.items() if k not in ["cv_content"]
            }
            print(json.dumps(clean_state, indent=2, default=str))
            return

        # Calculate execution time
        elapsed_time = ""
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_time = f" (Completed in {elapsed:.1f}s)"

        panel_title = f"🎉 Workflow Complete{elapsed_time}"

        summary_text = Text()
        summary_text.append("📊 Summary:\n", style="bold blue")
        summary_text.append(
            f"  • Jobs Found: {final_state.get('total_jobs_found', 0)}\n", style="green"
        )
        summary_text.append(
            f"  • Jobs Filtered: {len(final_state.get('filtered_jobs', []))}\n",
            style="yellow",
        )
        summary_text.append(
            f"  • Applications Submitted: {final_state.get('total_jobs_applied', 0)}\n",
            style="cyan",
        )

        if final_state.get("errors"):
            summary_text.append(
                f"  • Errors: {len(final_state['errors'])}\n", style="red"
            )

        summary_text.append(
            f"\n✅ Status: {final_state.get('current_status', 'Complete')}",
            style="bold green",
        )

        panel = Panel(summary_text, title=panel_title, border_style="green")

        if self.output_format == "rich":
            self.console.print(panel)
        else:
            self.console.print(f"Workflow Complete{elapsed_time}")
            self.console.print(f"Jobs Found: {final_state.get('total_jobs_found', 0)}")
            self.console.print(
                f"Jobs Filtered: {len(final_state.get('filtered_jobs', []))}"
            )
            self.console.print(
                f"Applications Submitted: {final_state.get('total_jobs_applied', 0)}"
            )
            if final_state.get("errors"):
                self.console.print(f"Errors: {len(final_state['errors'])}")

    def print_errors(self, errors: List[str]):
        """Print errors encountered during execution."""
        if not errors:
            return

        if self.output_format == "json":
            print(json.dumps({"errors": errors}, indent=2))
            return

        self.console.print("\n❌ Errors encountered:", style="bold red")
        for i, error in enumerate(errors, 1):
            if self.output_format == "rich":
                self.console.print(f"  {i}. {error}", style="red")
            else:
                self.console.print(f"  {i}. {error}")

    def start_timer(self):
        """Start timing the workflow."""
        self.start_time = time.time()

    def print_company_filter_menu(
        self, column_name: str, unique_values: List[str]
    ) -> List[str]:
        """Display unique values for a column and prompt user to select.

        Returns list of selected values, or empty list for 'all'.
        """
        table = Table(
            title=f"Available {column_name.title()} values",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("#", style="cyan", width=4)
        table.add_column(column_name.title(), style="green")

        for i, value in enumerate(unique_values, 1):
            table.add_row(str(i), value)

        self.console.print(table)
        self.console.print()

        selection = self.console.input(
            f"Select {column_name} (comma-separated numbers, or 'all'): "
        ).strip()

        if not selection or selection.lower() == "all":
            return []

        selected = []
        for part in selection.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(unique_values):
                    selected.append(unique_values[idx])

        return selected

    def print_filtered_companies_summary(
        self, companies: List[Dict[str, Any]], total: int
    ):
        """Print summary of filtered companies."""
        self.console.print(
            f"\nFiltered to [bold green]{len(companies)}[/bold green] companies "
            f"(from {total} total)\n"
        )

        if not companies:
            return

        table = Table(
            title="Sample Companies",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Name", style="cyan")
        table.add_column("Industry", style="green")
        table.add_column("Country", style="yellow")
        table.add_column("Size", style="blue")

        for company in companies[:10]:
            table.add_row(
                company.get("name", ""),
                company.get("industry", ""),
                company.get("country", ""),
                company.get("size", ""),
            )

        if len(companies) > 10:
            table.add_row("...", "...", "...", "...")

        self.console.print(table)
        self.console.print()

    def print_outreach_results(self, message_results: List[Dict[str, Any]]):
        """Print outreach message results."""
        if not message_results:
            self.console.print("No messages sent", style="yellow")
            return

        table = Table(
            title="Outreach Results",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Employee", style="cyan")
        table.add_column("Method", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Error", style="red", max_width=40)

        successful = 0
        for result in message_results:
            status = "Sent" if result.get("sent") else "Failed"
            if result.get("sent"):
                successful += 1
            error = result.get("error", "") or ""
            table.add_row(
                result.get("employee_name", "Unknown"),
                result.get("method", ""),
                status,
                error[:40] + "..." if len(error) > 40 else error,
            )

        self.console.print(table)
        self.console.print(
            f"\n[bold]Total: {successful}/{len(message_results)} messages sent[/bold]\n"
        )

    def print_outreach_summary(self, final_state: Dict[str, Any]):
        """Print final outreach workflow summary."""
        elapsed_time = ""
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_time = f" (Completed in {elapsed:.1f}s)"

        summary_text = Text()
        summary_text.append("Summary:\n", style="bold blue")
        summary_text.append(
            f"  Companies processed: {len(final_state.get('companies', []))}\n",
            style="green",
        )
        summary_text.append(
            f"  Employees found: {len(final_state.get('employees_found', []))}\n",
            style="cyan",
        )
        summary_text.append(
            f"  Messages sent: {final_state.get('messages_sent_today', 0)}\n",
            style="yellow",
        )

        if final_state.get("errors"):
            summary_text.append(
                f"  Errors: {len(final_state['errors'])}\n", style="red"
            )

        summary_text.append(
            f"\nStatus: {final_state.get('current_status', 'Complete')}",
            style="bold green",
        )

        panel = Panel(
            summary_text,
            title=f"Outreach Complete{elapsed_time}",
            border_style="green",
        )
        self.console.print(panel)

    def prompt_message_template(self) -> str:
        """Prompt user for message template (inline or file path)."""
        self.console.print(
            "\nEnter message template. Use {employee_name}, {company_name}, "
            "{employee_title}, {my_name}, {my_role} as placeholders.",
            style="bold blue",
        )
        self.console.print(
            "Enter a file path starting with '/' or './' to load from file.",
        )
        self.console.print(
            "Or type your message (end with an empty line):\n",
        )

        lines = []
        while True:
            line = self.console.input("")
            if line == "":
                if lines:
                    break
                continue
            lines.append(line)

        text = "\n".join(lines)

        # Check if it's a file path
        if text.startswith("/") or text.startswith("./"):
            from pathlib import Path

            path = Path(text.strip())
            if path.exists():
                return path.read_text(encoding="utf-8")
            else:
                self.console.print(f"File not found: {text}", style="red")
                return self.prompt_message_template()

        return text

    def prompt_template_variables(self) -> Dict[str, str]:
        """Prompt user for static template variables."""
        self.console.print("\nStatic template variables:", style="bold blue")
        variables = {}

        my_name = self.console.input("Your name: ").strip()
        if my_name:
            variables["my_name"] = my_name

        my_role = self.console.input("Your role/title: ").strip()
        if my_role:
            variables["my_role"] = my_role

        topic = self.console.input("Topic/reason for outreach (optional): ").strip()
        if topic:
            variables["topic"] = topic

        custom_closing = self.console.input("Custom closing (optional): ").strip()
        if custom_closing:
            variables["custom_closing"] = custom_closing

        return variables

    def prompt_user_input(self, message: str, default: Optional[str] = None) -> str:
        """Prompt user for input."""
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "

        return self.console.input(prompt) or default

    # === Role Group Methods ===

    def print_role_groups(self, role_groups: Dict[str, List[Dict[str, Any]]]) -> None:
        """Display clustered role groups with employee counts and samples."""
        self.console.print("\n[bold blue]Employees Clustered by Role[/bold blue]\n")

        total = sum(len(emps) for emps in role_groups.values())

        for role, employees in role_groups.items():
            if not employees:
                continue

            count = len(employees)
            percentage = (count / total * 100) if total > 0 else 0

            table = Table(
                title=f"{role} ({count} employees, {percentage:.1f}%)",
                show_header=True,
                header_style="bold magenta",
                title_style="bold cyan",
            )
            table.add_column("Name", style="green")
            table.add_column("Title", style="yellow")
            table.add_column("Company", style="blue")

            # Show first 5 employees as sample
            for emp in employees[:5]:
                table.add_row(
                    emp.get("name", ""),
                    emp.get("title", ""),
                    emp.get("company_name", ""),
                )

            if count > 5:
                table.add_row("...", f"and {count - 5} more", "...")

            self.console.print(table)
            self.console.print()

        self.console.print(f"[bold]Total employees: {total}[/bold]\n")

    def prompt_group_selection(
        self, role_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """Prompt user to select which role groups to message.

        Returns list of selected role names.
        """
        non_empty = [(role, len(emps)) for role, emps in role_groups.items() if emps]

        if not non_empty:
            self.console.print("No role groups with employees", style="yellow")
            return []

        table = Table(
            title="Select Role Groups to Message",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("#", style="cyan", width=4)
        table.add_column("Role", style="green")
        table.add_column("Count", style="yellow")

        for i, (role, count) in enumerate(non_empty, 1):
            table.add_row(str(i), role, str(count))

        self.console.print(table)
        self.console.print()

        selection = self.console.input(
            "Select groups (comma-separated numbers, or 'all'): "
        ).strip()

        if not selection or selection.lower() == "all":
            return [role for role, _ in non_empty]

        selected = []
        for part in selection.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(non_empty):
                    selected.append(non_empty[idx][0])

        return selected

    def prompt_template_for_role(
        self,
        role: str,
        employee_count: int,
        default_template: Optional[str] = None,
    ) -> tuple[str, Dict[str, str]]:
        """Prompt for message template and variables for a specific role.

        Returns (template, variables) tuple.
        """
        self.console.print(
            f"\n[bold cyan]Message Template for {role} ({employee_count} employees)[/bold cyan]"
        )

        if default_template:
            self.console.print(f"Default template: {default_template[:100]}...")
            use_default = self.console.input("Use default? [Y/n]: ").strip().lower()
            if use_default != "n":
                variables = self.prompt_template_variables()
                return default_template, variables

        template = self.prompt_message_template()
        variables = self.prompt_template_variables()
        return template, variables

    def print_message_preview(
        self,
        role: str,
        template: str,
        variables: Dict[str, str],
        sample_employee: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Preview a rendered message and ask for confirmation.

        Returns True if user confirms, False to re-enter template.
        """
        # Render with sample data
        preview_vars = {**variables}
        if sample_employee:
            preview_vars.update(
                {
                    "employee_name": sample_employee.get("name", "John Doe"),
                    "company_name": sample_employee.get("company_name", "Acme Corp"),
                    "employee_title": sample_employee.get("title", "Software Engineer"),
                }
            )
        else:
            preview_vars.update(
                {
                    "employee_name": "John Doe",
                    "company_name": "Acme Corp",
                    "employee_title": "Software Engineer",
                }
            )

        # Simple template rendering for preview
        preview = template
        for key, value in preview_vars.items():
            preview = preview.replace(f"{{{key}}}", value)

        panel = Panel(
            preview,
            title=f"Message Preview for {role}",
            border_style="green",
        )
        self.console.print(panel)

        confirm = self.console.input("Send this template? [Y/n]: ").strip().lower()
        return confirm != "n"

    def print_outreach_results_by_role(
        self,
        message_results: List[Dict[str, Any]],
        results_by_role: Dict[str, Dict[str, Any]],
    ) -> None:
        """Print outreach results grouped by role."""
        if not message_results:
            self.console.print("No messages sent", style="yellow")
            return

        # Summary by role
        self.console.print("\n[bold blue]Results by Role[/bold blue]\n")

        summary_table = Table(
            title="Summary by Role",
            show_header=True,
            header_style="bold magenta",
        )
        summary_table.add_column("Role", style="cyan")
        summary_table.add_column("Sent", style="green")
        summary_table.add_column("Failed", style="red")
        summary_table.add_column("Total", style="yellow")

        for role, stats in results_by_role.items():
            sent = stats.get("sent", 0)
            failed = stats.get("failed", 0)
            summary_table.add_row(role, str(sent), str(failed), str(sent + failed))

        self.console.print(summary_table)
        self.console.print()

        # Detailed results (optional)
        total_sent = sum(1 for r in message_results if r.get("sent"))
        total = len(message_results)

        self.console.print(
            f"[bold]Total: {total_sent}/{total} messages sent successfully[/bold]\n"
        )

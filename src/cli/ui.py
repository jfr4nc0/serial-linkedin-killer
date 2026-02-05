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

    def _display_values_table(
        self, column_name: str, values: List[str], offset: int = 0
    ) -> None:
        """Display a numbered table of values."""
        table = Table(
            title=f"Available {column_name.title()} values ({len(values)} total)",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("#", style="cyan", width=6)
        table.add_column(column_name.title(), style="green")

        for i, value in enumerate(values, offset + 1):
            table.add_row(str(i), value)

        self.console.print(table)

    def print_company_filter_menu(
        self, column_name: str, unique_values: List[str]
    ) -> List[str]:
        """Display unique values for a column and prompt user to select.

        Supports:
        - Numbers: "1,3,5" to select by index
        - Search: any text to filter values by substring match
        - 'all': select all / skip filter
        - 'list': show full list again

        Returns list of selected values, or empty list for 'all'.
        """
        selected = []

        # Show initial list (truncated if too many)
        if len(unique_values) > 30:
            self._display_values_table(column_name, unique_values[:30])
            self.console.print(
                f"  ... and {len(unique_values) - 30} more. "
                "Type to search or enter numbers.\n",
                style="dim",
            )
        else:
            self._display_values_table(column_name, unique_values)

        self.console.print()
        self.console.print(
            f"  [dim]Enter numbers (1,3,5), search text to filter, "
            f"'all' to skip, ENTER to confirm selection[/dim]"
        )

        while True:
            prompt = (
                f"Select {column_name}"
                + (f" [selected: {len(selected)}]" if selected else "")
                + ": "
            )
            raw = self.console.input(prompt).strip()

            if not raw:
                return selected

            if raw.lower() in ("all", "skip"):
                return []

            if raw.lower() == "list":
                self._display_values_table(column_name, unique_values)
                continue

            # Check if input is numbers (comma-separated)
            parts = raw.split(",")
            all_numeric = all(p.strip().isdigit() for p in parts if p.strip())

            if all_numeric and parts[0].strip():
                for part in parts:
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(unique_values):
                            val = unique_values[idx]
                            if val not in selected:
                                selected.append(val)
                                self.console.print(f"  + {val}", style="green")
                            else:
                                self.console.print(
                                    f"  (already selected: {val})", style="dim"
                                )
                        else:
                            self.console.print(f"  Invalid number: {part}", style="red")
                continue

            # Text search: filter values by substring
            query = raw.lower()
            matches = [
                (i, v) for i, v in enumerate(unique_values) if query in v.lower()
            ]

            if not matches:
                self.console.print(f"  No matches for '{raw}'", style="yellow")
                continue

            # Display matches with their original index
            match_table = Table(
                title=f"Matches for '{raw}'",
                show_header=True,
                header_style="bold magenta",
            )
            match_table.add_column("#", style="cyan", width=6)
            match_table.add_column(column_name.title(), style="green")

            for orig_idx, value in matches:
                match_table.add_row(str(orig_idx + 1), value)

            self.console.print(match_table)
            self.console.print(
                "  [dim]Enter numbers to select from above, or keep searching[/dim]"
            )

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

    def edit_in_editor(self, content: str = "", header_comment: str = "") -> str:
        """Open $EDITOR to edit text content. Returns edited text.

        Args:
            content: Initial content to edit.
            header_comment: Comment block placed at top of file (stripped on return).
        """
        import os
        import subprocess
        import tempfile

        editor = os.environ.get("EDITOR", "vim")

        file_content = ""
        if header_comment:
            # Prefix each line with #
            for line in header_comment.strip().splitlines():
                file_content += f"# {line}\n"
            file_content += "#\n# Lines starting with # are ignored.\n"
            file_content += "# Save and close the editor when done.\n\n"

        file_content += content

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="outreach_template_", delete=False
        ) as f:
            f.write(file_content)
            tmp_path = f.name

        try:
            subprocess.run([editor, tmp_path], check=True)

            with open(tmp_path, "r", encoding="utf-8") as f:
                edited = f.read()

            # Strip comment lines
            lines = [line for line in edited.splitlines() if not line.startswith("#")]

            # Strip leading/trailing blank lines
            result = "\n".join(lines).strip()
            return result

        except subprocess.CalledProcessError:
            self.console.print(
                "Editor exited with error, keeping original", style="yellow"
            )
            return content
        finally:
            os.unlink(tmp_path)

    def prompt_message_template(self, initial_content: str = "") -> str:
        """Prompt user for message template (editor, inline, or file path)."""
        import os

        placeholders = (
            "Available placeholders:\n"
            "  {employee_name}  - Full name of the employee\n"
            "  {first_name}     - First name only\n"
            "  {company_name}   - Company name\n"
            "  {employee_title} - Job title\n"
            "  {my_name}        - Your name\n"
            "  {my_role}        - Your role/title\n"
            "  {topic}          - Topic/reason for outreach\n"
            "  {custom_closing} - Custom closing"
        )

        editor = os.environ.get("EDITOR", "vim")
        self.console.print(
            f"\n[bold blue]Enter message template:[/bold blue]",
        )
        self.console.print(f"  e - Open in editor ({editor})")
        self.console.print("  f - Load from file path")
        self.console.print("  i - Type inline (end with empty line)")

        choice = self.console.input("\nChoice [e]: ").strip().lower() or "e"

        if choice == "e":
            return self.edit_in_editor(initial_content, placeholders)

        elif choice == "f":
            from pathlib import Path

            file_path = self.console.input("File path: ").strip()
            path = Path(file_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
            else:
                self.console.print(f"File not found: {file_path}", style="red")
                return self.prompt_message_template(initial_content)

        else:
            # Inline input
            self.console.print(
                f"\n{placeholders}\n",
                style="dim",
            )
            self.console.print("Type your message (end with an empty line):\n")

            lines = []
            while True:
                line = self.console.input("")
                if line == "":
                    if lines:
                        break
                    continue
                lines.append(line)

            return "\n".join(lines)

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

    # === Contacted Companies ===

    def print_contacted_companies(self, companies: list) -> None:
        """Display table of already-contacted companies."""
        if not companies:
            self.console.print("[dim]No companies have been contacted yet.[/dim]")
            return

        table = Table(title="Already Contacted Companies", show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", style="cyan")
        table.add_column("Employees Messaged", justify="right", style="green")

        for i, company in enumerate(companies, 1):
            table.add_row(
                str(i),
                company.get("company_name", "Unknown"),
                str(company.get("employee_count", 0)),
            )

        self.console.print(table)

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

    def prompt_role_reassignment(
        self, role_groups: Dict[str, List[Dict[str, Any]]]
    ) -> tuple:
        """Let the user reassign employees between roles to fix LLM mistakes.

        Shows all employees with a global index, lets the user pick one and
        choose a new role.  Loops until the user presses Enter to finish.

        Returns (role_groups, reassignments_map) where reassignments_map is
        {profile_url: new_role} for the server to apply.
        """
        reassign = (
            self.console.input("Reassign employees between roles? [y/N]: ")
            .strip()
            .lower()
        )
        if reassign != "y":
            return role_groups, {}

        reassignments: Dict[str, str] = {}

        # Build a flat indexed list: (global_idx, role, employee_dict)
        while True:
            flat: list[tuple[str, dict]] = []
            roles = [r for r in role_groups if role_groups[r]]
            for role in roles:
                for emp in role_groups[role]:
                    flat.append((role, emp))

            if not flat:
                self.console.print("No employees to reassign", style="yellow")
                break

            # Display all employees with a global number
            table = Table(
                title="All Employees by Role",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("#", style="cyan", width=5)
            table.add_column("Name", style="green")
            table.add_column("Title", style="yellow")
            table.add_column("Company", style="blue")
            table.add_column("Current Role", style="magenta")

            for i, (role, emp) in enumerate(flat, 1):
                table.add_row(
                    str(i),
                    emp.get("name", ""),
                    emp.get("title", ""),
                    emp.get("company_name", ""),
                    role,
                )

            self.console.print(table)
            self.console.print()

            pick = self.console.input(
                "Employee # to reassign (Enter to finish): "
            ).strip()

            if not pick:
                break

            if not pick.isdigit():
                self.console.print("Enter a number", style="red")
                continue

            idx = int(pick) - 1
            if idx < 0 or idx >= len(flat):
                self.console.print("Invalid number", style="red")
                continue

            current_role, emp = flat[idx]
            emp_name = emp.get("name", "Unknown")
            self.console.print(
                f"\n[bold]{emp_name}[/bold] is currently in "
                f"[cyan]{current_role}[/cyan]"
            )

            # Show target role options
            self.console.print("\nMove to:")
            for i, role in enumerate(roles, 1):
                marker = " (current)" if role == current_role else ""
                self.console.print(f"  {i}. {role}{marker}")

            target = self.console.input("Target role #: ").strip()
            if not target.isdigit():
                self.console.print("Cancelled", style="yellow")
                continue

            target_idx = int(target) - 1
            if target_idx < 0 or target_idx >= len(roles):
                self.console.print("Invalid number", style="red")
                continue

            new_role = roles[target_idx]
            if new_role == current_role:
                self.console.print("Same role, no change", style="dim")
                continue

            # Move the employee
            role_groups[current_role].remove(emp)
            role_groups[new_role].append(emp)

            # Track reassignment for the server
            profile_url = emp.get("profile_url", "")
            if profile_url:
                reassignments[profile_url] = new_role

            # Clean up empty groups
            if not role_groups[current_role]:
                del role_groups[current_role]

            self.console.print(
                f"Moved [bold]{emp_name}[/bold] -> [cyan]{new_role}[/cyan]",
                style="green",
            )

        # Show updated summary
        self.console.print("\n[bold]Updated role groups:[/bold]")
        for role, emps in role_groups.items():
            if emps:
                self.console.print(f"  {role}: {len(emps)} employees")
        self.console.print()

        return role_groups, reassignments

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

        selection = (
            self.console.input("Select groups (comma-separated numbers, or 'all'): ")
            .strip()
            .strip("'\"")
        )

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
    ) -> str:
        """Preview a rendered message and ask for confirmation.

        Returns:
            "confirm" - user approved the template
            "edit"    - user wants to edit the template in $EDITOR
            "reject"  - user wants to start over with a new template
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

        # Use render_template for preview (extracts first name from employee_name)
        from src.core.agents.tools.message_template import render_template

        preview = render_template(template, preview_vars)

        panel = Panel(
            preview,
            title=f"Message Preview for {role}",
            border_style="green",
        )
        self.console.print(panel)

        choice = (
            self.console.input("Send this template? [Y/n/e(dit)]: ").strip().lower()
        )
        if choice in ("e", "edit"):
            return "edit"
        elif choice == "n":
            return "reject"
        return "confirm"

    def review_all_templates(
        self,
        selected_groups_config: Dict[str, Dict[str, Any]],
        role_groups: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Dict[str, Any]]:
        """Show a summary of all configured templates and let the user edit any.

        Returns the (possibly modified) selected_groups_config.
        """
        from src.core.agents.tools.message_template import render_template

        while True:
            self.console.print("\n[bold blue]Template Summary[/bold blue]\n")

            roles = list(selected_groups_config.keys())
            for i, role in enumerate(roles, 1):
                cfg = selected_groups_config[role]
                template = cfg["message_template"]
                count = len(role_groups.get(role, []))
                # Show truncated template
                preview_line = template.replace("\n", " ")
                if len(preview_line) > 80:
                    preview_line = preview_line[:77] + "..."
                self.console.print(
                    f"  {i}. [cyan]{role}[/cyan] ({count} employees): {preview_line}"
                )

            self.console.print()
            choice = self.console.input(
                "Edit a template? (number to edit, Enter to continue): "
            ).strip()

            if not choice:
                break

            if not choice.isdigit():
                continue

            idx = int(choice) - 1
            if idx < 0 or idx >= len(roles):
                self.console.print("Invalid number", style="red")
                continue

            role = roles[idx]
            cfg = selected_groups_config[role]
            template = cfg["message_template"]
            variables = cfg["template_variables"]
            employees_in_role = role_groups.get(role, [])
            sample_employee = employees_in_role[0] if employees_in_role else None

            # Edit-preview loop for the selected role
            template = self.edit_in_editor(
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

            # Preview updated template
            while True:
                result = self.print_message_preview(
                    role, template, variables, sample_employee
                )
                if result == "confirm":
                    break
                elif result == "edit":
                    template = self.edit_in_editor(
                        template,
                        header_comment=f"Editing template for: {role}",
                    )
                else:
                    # reject: re-open editor with current content
                    template = self.edit_in_editor(
                        template,
                        header_comment=f"Editing template for: {role}",
                    )

            selected_groups_config[role]["message_template"] = template

        return selected_groups_config

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

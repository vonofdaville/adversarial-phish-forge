#!/usr/bin/env python3
"""
CHIMERA CLI - Main Command Line Interface

WARNING: This tool is designed for AUTHORIZED RED TEAM OPERATIONS ONLY.
Unauthorized use may constitute violations of:
- 18 U.S.C. § 1030 (Computer Fraud and Abuse Act)
- 18 U.S.C. § 2701 (Stored Communications Act)
- EU GDPR Articles 5, 9, 32
- CCPA § 1798.100
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import httpx

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.config import config, validate_config
from ..utils.logger import setup_logging

# Initialize
console = Console()
logger = setup_logging(__name__)

# CLI app
app = typer.Typer(
    name="chimera-cli",
    help="CHIMERA - Cognitive Heuristic Intelligence for Multi-stage Engagement Research & Assessment",
    add_completion=False,
)

# Sub-apps for organization
campaign_app = typer.Typer(help="Campaign management commands")
consent_app = typer.Typer(help="Consent database management")
system_app = typer.Typer(help="System administration commands")
analytics_app = typer.Typer(help="Analytics and reporting commands")

app.add_typer(campaign_app, name="campaign")
app.add_typer(consent_app, name="consent")
app.add_typer(system_app, name="system")
app.add_typer(analytics_app, name="analytics")


# Utility functions
def check_api_connectivity() -> bool:
    """Check if the orchestrator API is accessible."""
    try:
        response = httpx.get(f"http://localhost:{config.orchestrator_port}/health", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


def make_api_request(method: str, endpoint: str, **kwargs) -> Optional[dict]:
    """Make API request to orchestrator."""
    base_url = f"http://localhost:8000"  # Assuming orchestrator runs on 8000
    url = f"{base_url}{endpoint}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API Error: {e.response.status_code} - {e.response.text}[/red]")
    except httpx.RequestError as e:
        console.print(f"[red]Request Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected Error: {e}[/red]")

    return None


def display_banner():
    """Display CHIMERA banner."""
    banner = """
[bold cyan]
 ██████╗██╗  ██╗██╗███╗   ███╗███████╗██████╗  █████╗
██╔════╝██║  ██║██║████╗ ████║██╔════╝██╔══██╗██╔══██╗
██║     ███████║██║██╔████╔██║█████╗  ██████╔╝███████║
██║     ██╔══██║██║██║╚██╔╝██║██╔══╝  ██╔══██╗██╔══██║
╚██████╗██║  ██║██║██║ ╚═╝ ██║███████╗██║  ██║██║  ██║
 ╚═════╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
[/bold cyan]

[bold yellow]Cognitive Heuristic Intelligence for Multi-stage Engagement Research & Assessment[/bold yellow]
[red]⚠️  AUTHORIZED RED TEAM OPERATIONS ONLY  ⚠️[/red]

Version: {config.app_version}
Date: December 2025
Codename: ADVERSARIAL-PHISH-FORGE
"""
    console.print(banner)


# Root command
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config_check: bool = typer.Option(False, "--check-config", help="Validate configuration and exit")
):
    """CHIMERA CLI - Red Team Campaign Management"""
    if config_check:
        console.print("[bold]Validating CHIMERA configuration...[/bold]")

        # Validate configuration
        config_issues = validate_config()
        if config_issues:
            console.print("[red]Configuration Issues Found:[/red]")
            for issue in config_issues:
                console.print(f"  • {issue}")
            sys.exit(1)
        else:
            console.print("[green]✓ Configuration validation passed[/green]")

        # Check API connectivity
        if check_api_connectivity():
            console.print("[green]✓ Orchestrator API is accessible[/green]")
        else:
            console.print("[yellow]⚠ Orchestrator API is not accessible[/yellow]")
            console.print("  Make sure the orchestrator is running: docker-compose up orchestrator")

        sys.exit(0)

    if verbose:
        logger.setLevel("DEBUG")

    display_banner()


# Campaign commands
@campaign_app.command("create")
def campaign_create(
    name: str = typer.Option(..., "--name", "-n", help="Campaign name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Campaign description"),
    campaign_type: str = typer.Option(..., "--type", "-t", help="Campaign type (phishing, vishing, etc.)"),
    target_file: Path = typer.Option(..., "--targets", "-f", help="Path to target list CSV"),
    approval_required: bool = typer.Option(True, "--approval-required", help="Require human approval"),
    ethical_constraints: Optional[List[str]] = typer.Option(
        None, "--constraints", "-c",
        help="Ethical constraints (comma-separated: no_threats,include_opt_out,etc.)"
    )
):
    """Create a new red team campaign."""
    console.print(f"[bold]Creating campaign: {name}[/bold]")

    # Parse ethical constraints
    constraints = {}
    if ethical_constraints:
        for constraint in ethical_constraints:
            constraints[constraint] = True
    else:
        # Default ethical constraints
        constraints = {
            "no_threats": True,
            "include_opt_out": True,
            "no_personal_data": True,
            "educational_content": True
        }

    # Load targets from file
    if not target_file.exists():
        console.print(f"[red]Target file not found: {target_file}[/red]")
        sys.exit(1)

    targets = []
    try:
        with open(target_file, 'r') as f:
            # Simple CSV parsing (email,participant_id format)
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) >= 2:
                        targets.append({
                            'participant_id': parts[0].strip(),
                            'email': parts[1].strip()
                        })
    except Exception as e:
        console.print(f"[red]Error reading target file: {e}[/red]")
        sys.exit(1)

    if not targets:
        console.print("[red]No valid targets found in file[/red]")
        sys.exit(1)

    console.print(f"Loaded {len(targets)} targets")

    # Prepare campaign data
    campaign_data = {
        "name": name,
        "description": description,
        "campaign_type": campaign_type,
        "target_participants": [t['participant_id'] for t in targets],
        "ethical_constraints": constraints,
        "created_by": "cli_user"  # In production, get from authentication
    }

    # Make API request
    with console.status("[bold green]Creating campaign..."):
        result = make_api_request("POST", "/campaigns", json=campaign_data)

    if result:
        console.print("[green]✓ Campaign created successfully[/green]")
        console.print(f"Campaign ID: [bold]{result['campaign_id']}[/bold]")
        console.print(f"Status: {result['status']}")
        console.print(f"Participants: {result['participant_count']}")

        if result.get('requires_approval'):
            console.print("\n[yellow]⚠ This campaign requires approval before launch[/yellow]")
            console.print("Use: chimera-cli campaign approve <campaign_id>")
    else:
        console.print("[red]✗ Failed to create campaign[/red]")
        sys.exit(1)


@campaign_app.command("list")
def campaign_list(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum campaigns to show")
):
    """List campaigns."""
    params = {}
    if status:
        params["status"] = status
    if limit:
        params["limit"] = limit

    result = make_api_request("GET", "/campaigns", params=params)

    if result:
        table = Table(title="CHIMERA Campaigns")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("Participants", style="magenta", justify="right")

        for campaign in result.get("campaigns", []):
            table.add_row(
                campaign["id"][:8] + "...",
                campaign["name"],
                campaign["campaign_type"],
                campaign["status"],
                campaign["created_at"][:10],
                str(campaign.get("participant_count", 0))
            )

        console.print(table)
    else:
        console.print("[red]Failed to retrieve campaigns[/red]")


@campaign_app.command("approve")
def campaign_approve(
    campaign_id: str = typer.Argument(..., help="Campaign ID to approve"),
    approved_by: str = typer.Option(..., "--approved-by", "-a", help="Approver name")
):
    """Approve a campaign for execution."""
    console.print(f"[bold]Approving campaign: {campaign_id}[/bold]")
    console.print("[yellow]⚠ This action will enable campaign execution[/yellow]")

    # Confirm approval
    if not typer.confirm("Are you sure you want to approve this campaign?"):
        console.print("Approval cancelled")
        return

    approval_data = {"approved_by": approved_by}

    with console.status("[bold green]Approving campaign..."):
        result = make_api_request("POST", f"/campaigns/{campaign_id}/approve", json=approval_data)

    if result:
        console.print("[green]✓ Campaign approved successfully[/green]")
        console.print(f"Status: {result.get('status', 'approved')}")
    else:
        console.print("[red]✗ Failed to approve campaign[/red]")
        sys.exit(1)


@campaign_app.command("terminate")
def campaign_terminate(
    campaign_id: str = typer.Argument(..., help="Campaign ID to terminate"),
    reason: str = typer.Option(..., "--reason", "-r", help="Termination reason"),
    terminated_by: str = typer.Option(..., "--by", "-b", help="Terminator name")
):
    """Terminate a running campaign (emergency kill switch)."""
    console.print(f"[bold red]🚨 TERMINATING CAMPAIGN: {campaign_id}[/red]")
    console.print(f"Reason: {reason}")
    console.print("[red]⚠ This will immediately stop all campaign activities[/red]")

    if not typer.confirm("Are you absolutely sure you want to terminate this campaign?"):
        console.print("Termination cancelled")
        return

    termination_data = {
        "campaign_id": campaign_id,
        "reason": reason,
        "triggered_by": terminated_by
    }

    with console.status("[bold red]Terminating campaign..."):
        result = make_api_request("POST", "/kill-switch", json=termination_data)

    if result:
        console.print("[red]✓ Campaign terminated[/red]")
        console.print(f"Affected participants: {result.get('affected_participants', 0)}")
        console.print(f"Termination time: {datetime.now().isoformat()}")
    else:
        console.print("[red]✗ Failed to terminate campaign[/red]")
        sys.exit(1)


@campaign_app.command("monitor")
def campaign_monitor(
    campaign_id: Optional[str] = typer.Option(None, "--id", help="Specific campaign ID"),
    live: bool = typer.Option(False, "--live", "-l", help="Live monitoring mode")
):
    """Monitor campaign progress and metrics."""
    if live:
        console.print("[green]Starting live campaign monitoring...[/green]")
        console.print("Press Ctrl+C to stop")

        try:
            while True:
                if campaign_id:
                    result = make_api_request("GET", f"/campaigns/{campaign_id}")
                    if result:
                        display_campaign_status(result)
                else:
                    # Show system-wide status
                    result = make_api_request("GET", "/system/status")
                    if result:
                        display_system_status(result)

                console.print("\n" + "="*50)
                asyncio.sleep(5)  # Update every 5 seconds

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")

    else:
        # Single status check
        if campaign_id:
            result = make_api_request("GET", f"/campaigns/{campaign_id}")
            if result:
                display_campaign_status(result)
        else:
            result = make_api_request("GET", "/system/status")
            if result:
                display_system_status(result)


# Consent commands
@consent_app.command("register")
def consent_register(
    participant_email: str = typer.Option(..., "--email", "-e", help="Participant email"),
    participant_role: str = typer.Option(..., "--role", "-r", help="Participant role"),
    campaign_types: List[str] = typer.Option(..., "--types", "-t", help="Allowed campaign types"),
    expiration_days: int = typer.Option(365, "--expiration", help="Consent expiration in days"),
    legal_officer: str = typer.Option(..., "--officer", "-o", help="Legal signoff officer")
):
    """Register participant consent."""
    console.print(f"[bold]Registering consent for: {participant_email}[/bold]")

    consent_data = {
        "participant_email": participant_email,
        "participant_role": participant_role,
        "campaign_types_allowed": campaign_types,
        "expiration_days": expiration_days,
        "legal_signoff_officer": legal_officer,
        "created_by": "cli_user"
    }

    result = make_api_request("POST", "/consent/register", json=consent_data)

    if result:
        console.print("[green]✓ Consent registered successfully[/green]")
        console.print(f"Participant ID: [bold]{result['participant_id']}[/bold]")
        console.print(f"Consent Hash: {result['consent_hash'][:16]}...")
        console.print(f"Expires: {result['expiration_date']}")
    else:
        console.print("[red]✗ Failed to register consent[/red]")
        sys.exit(1)


@consent_app.command("validate")
def consent_validate(
    participant_id: str = typer.Option(..., "--participant", "-p", help="Participant ID"),
    campaign_type: Optional[str] = typer.Option(None, "--type", "-t", help="Campaign type to check")
):
    """Validate participant consent."""
    console.print(f"[bold]Validating consent for participant: {participant_id}[/bold]")

    validation_data = {
        "participant_id": participant_id,
        "campaign_type": campaign_type
    }

    result = make_api_request("POST", "/consent/validate", json=validation_data)

    if result and result.get("valid"):
        console.print("[green]✓ Consent is valid[/green]")
        console.print(f"Organization: {result.get('organization_id', 'Unknown')}")
        console.print(f"Expires: {result.get('expiration_date', 'Unknown')}")
        console.print(f"Allowed types: {', '.join(result.get('campaign_types_allowed', []))}")

        gates = result.get("gates", {})
        console.print(f"Gates - Legal: {gates.get('legal', False)}, Consent: {gates.get('consent', False)}, Operational: {gates.get('operational', False)}")
    else:
        console.print("[red]✗ Consent validation failed[/red]")
        if result:
            console.print(f"Reason: {result.get('reason', 'Unknown')}")
        sys.exit(1)


@consent_app.command("summary")
def consent_summary(
    organization_id: Optional[str] = typer.Option(None, "--org", "-o", help="Organization ID filter")
):
    """Get consent database summary."""
    params = {}
    if organization_id:
        params["organization_id"] = organization_id

    result = make_api_request("GET", "/consent/summary", params=params)

    if result:
        table = Table(title="Consent Database Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Total Consents", str(result.get("total_consents", 0)))
        table.add_row("Active Consents", str(result.get("active_consents", 0)))
        table.add_row("Revoked Consents", str(result.get("revoked_consents", 0)))
        table.add_row("Expired Consents", str(result.get("expired_consents", 0)))

        console.print(table)
    else:
        console.print("[red]Failed to retrieve consent summary[/red]")


# System commands
@system_app.command("status")
def system_status():
    """Get system health and status."""
    result = make_api_request("GET", "/system/status")

    if result:
        display_system_status(result)
    else:
        console.print("[red]Failed to get system status[/red]")
        console.print("Make sure the orchestrator is running: docker-compose up orchestrator")


@system_app.command("health")
def system_health():
    """Quick health check."""
    if check_api_connectivity():
        console.print("[green]✓ CHIMERA orchestrator is healthy[/green]")
        sys.exit(0)
    else:
        console.print("[red]✗ CHIMERA orchestrator is not responding[/red]")
        sys.exit(1)


# Analytics commands
@analytics_app.command("campaign")
def analytics_campaign(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    hours: int = typer.Option(24, "--hours", "-h", help="Analysis time window")
):
    """Get campaign analytics."""
    console.print(f"[bold]Analyzing campaign: {campaign_id}[/bold]")

    # This would typically call the telemetry engine
    # For now, show placeholder
    console.print(f"Time window: {hours} hours")
    console.print("[yellow]Analytics integration pending - use telemetry engine directly[/yellow]")


# Helper functions
def display_campaign_status(campaign: dict):
    """Display detailed campaign status."""
    panel = Panel.fit(
        f"[bold]Campaign: {campaign['name']}[/bold]\n"
        f"ID: {campaign['id']}\n"
        f"Type: {campaign['campaign_type']}\n"
        f"Status: [bold green]{campaign['status']}[/bold green]\n"
        f"Created: {campaign['created_at']}\n"
        f"Participants: {campaign.get('participant_count', 0)}\n"
        f"Progress: {campaign.get('progress', 'N/A')}",
        title="Campaign Status"
    )
    console.print(panel)


def display_system_status(status: dict):
    """Display system-wide status."""
    panel = Panel.fit(
        f"[bold]CHIMERA System Status[/bold]\n"
        f"Version: {status.get('version', 'Unknown')}\n"
        f"Status: [bold green]{status.get('status', 'Unknown')}[/bold green]\n"
        f"Active Campaigns: {status.get('campaign_statistics', {}).get('active_campaigns', 0)}\n"
        f"Total Participants: {status.get('consent_summary', {}).get('active_consents', 0)}\n"
        f"Kill Switch Events: {status.get('kill_switch_status', {}).get('total_kill_switches', 0)}",
        title="System Overview"
    )
    console.print(panel)


if __name__ == "__main__":
    app()


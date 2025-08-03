"""CLI interface for Runpod network storage management."""

import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.client import RunpodClient
from ..core.s3_client import RunpodS3Client


def prompt_datacenter(prompt_text: str, default: str = "EU-RO-1") -> str:
    """Prompt for datacenter with case-insensitive validation."""
    available = list(RunpodClient.get_available_datacenters().keys())
    choices_text = "/".join(available)
    full_prompt = f"{prompt_text} [{choices_text}]"
    
    while True:
        response = Prompt.ask(full_prompt, default=default)
        normalized = RunpodClient.normalize_datacenter(response)
        
        if normalized in available:
            return normalized
        
        console.print(f"[red]Invalid datacenter '{response}'. Available options: {', '.join(available)}[/red]")
        console.print("[yellow]Note: Input is case-insensitive[/yellow]")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


def setup_s3_client(datacenter_id: str, endpoint_url: str) -> RunpodS3Client:
    """Set up S3 client with user credentials."""
    access_key, secret_key = get_s3_credentials_interactively()

    return RunpodS3Client(
        access_key=access_key,
        secret_key=secret_key,
        region=datacenter_id,
        endpoint_url=endpoint_url,
    )


def get_api_key_interactively():
    """Prompt user for API key if not provided."""
    api_key = os.getenv("RUNPOD_API_KEY")

    if not api_key:
        console.print("\n[yellow]Welcome to Runpod Storage CLI![/yellow]")
        console.print("To get started, you'll need your Runpod API key.")
        console.print(
            "Get it from: [link]https://console.runpod.io/user/settings[/link]\n"
        )

        api_key = Prompt.ask("Please enter your Runpod API key", password=True)

        if Confirm.ask(
            "Would you like to save this API key as an environment variable for future use?"
        ):
            console.print(
                "\nAdd this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
            )
            console.print(f'[green]export RUNPOD_API_KEY="{api_key}"[/green]')
            console.print(
                f"\nOr run: [green]echo 'export RUNPOD_API_KEY=\"{api_key}\"' >> ~/.bashrc[/green]"
            )
            console.print("Then reload your shell: [green]source ~/.bashrc[/green]\n")

    return api_key


def get_s3_credentials_interactively():
    """Prompt user for S3 credentials if not provided."""
    access_key = os.getenv("RUNPOD_S3_ACCESS_KEY")
    secret_key = os.getenv("RUNPOD_S3_SECRET_KEY")

    if not access_key or not secret_key:
        console.print(
            "\n[yellow]For file operations, you'll also need S3 API credentials.[/yellow]"
        )
        console.print(
            "Get them from: [link]https://console.runpod.io/user/settings[/link] → S3 API Keys\n"
        )

        if not access_key:
            access_key = Prompt.ask("S3 Access Key (user_...)")

        if not secret_key:
            secret_key = Prompt.ask("S3 Secret Key (rps_...)", password=True)

        # Save to environment for this session
        os.environ["RUNPOD_S3_ACCESS_KEY"] = access_key
        os.environ["RUNPOD_S3_SECRET_KEY"] = secret_key

        if Confirm.ask(
            "Would you like to save these S3 credentials as environment variables?"
        ):
            console.print("\nAdd these to your shell profile:")
            console.print(f'[green]export RUNPOD_S3_ACCESS_KEY="{access_key}"[/green]')
            console.print(
                f'[green]export RUNPOD_S3_SECRET_KEY="{secret_key}"[/green]\n'
            )

    return access_key, secret_key


@click.group()
@click.option(
    "--api-key",
    envvar="RUNPOD_API_KEY",
    help="Runpod API key (or set RUNPOD_API_KEY env var)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, api_key, verbose):
    """Runpod Network Storage CLI - Manage volumes and files."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key


@cli.command()
@click.pass_context
def list_volumes(ctx):
    """List all network volumes."""
    try:
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching network volumes...", total=None)
            volumes = client.list_network_volumes()
            progress.update(task, completed=1)

        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            console.print("Create one with: [bold]runpod-storage create-volume[/bold]")
            return

        # Create a nice table
        table = Table(title="Network Volumes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Size (GB)", justify="right")
        table.add_column("Datacenter", style="blue")

        for volume in volumes:
            table.add_row(
                volume.get("id", "N/A"),
                volume.get("name", "N/A"),
                str(volume.get("size", "N/A")),
                volume.get("dataCenterId", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--name", prompt="Volume name", help="Name for the network volume")
@click.option("--size", type=int, prompt="Size in GB", help="Size in GB (10-4000)")
@click.option(
    "--datacenter",
    type=click.Choice(list(RunpodClient.get_available_datacenters().keys()), case_sensitive=False),
    help="Datacenter ID",
)
@click.pass_context
def create_volume(ctx, name, size, datacenter):
    """Create a new network volume."""
    try:
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)

        # Show available datacenters if not specified
        if not datacenter:
            console.print("\nAvailable datacenters:")
            for dc_id, endpoint in client.get_available_datacenters().items():
                console.print(f"  {dc_id}: {endpoint}")
            datacenter = prompt_datacenter("Choose datacenter")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating network volume...", total=None)
            normalized_datacenter = RunpodClient.normalize_datacenter(datacenter)
            volume = client.create_network_volume(name, size, normalized_datacenter)
            progress.update(task, completed=1)

        console.print("[green]✓[/green] Created network volume:")
        console.print(f"  ID: {volume['id']}")
        console.print(f"  Name: {volume['name']}")
        console.print(f"  Size: {volume['size']} GB")
        console.print(f"  Datacenter: {volume['dataCenterId']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("volume_id", required=False)
@click.option("--path", default="", help="Remote path to list (default: root)")
@click.pass_context
def list_files(ctx, volume_id, path):
    """List files in a network volume."""
    try:
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)

        # Get volume ID if not provided
        if not volume_id:
            volumes = client.list_network_volumes()
            if not volumes:
                console.print("[yellow]No network volumes found.[/yellow]")
                return

            console.print("Available volumes:")
            for i, vol in enumerate(volumes):
                console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

            choice = Prompt.ask(
                "Select volume",
                choices=[str(i + 1) for i in range(len(volumes))],
                default="1",
            )
            volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details for datacenter info
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Set up S3 client
        s3_client = setup_s3_client(datacenter_id, endpoint_url)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Listing files...", total=None)
            files = s3_client.list_files(volume_id, path)
            progress.update(task, completed=1)

        if not files:
            console.print(f"[yellow]No files found in volume {volume_id}[/yellow]")
            return

        # Create table
        table = Table(title=f"Files in {volume_id}/{path}")
        table.add_column("Path", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Last Modified", style="dim")

        for file_info in files:
            # Format size
            size = file_info["size"]
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"

            table.add_row(
                file_info["key"],
                size_str,
                file_info["last_modified"].strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("local_path", type=click.Path(exists=True))
@click.argument("volume_id", required=False)
@click.option("--remote-path", help="Remote path (default: same as local filename)")
@click.option(
    "--chunk-size",
    type=int,
    default=50 * 1024 * 1024,
    help="Chunk size for large files (default: 50MB)",
)
@click.option(
    "--no-resume",
    is_flag=True,
    help="Disable resume capability for interrupted uploads",
)
@click.pass_context
def upload(ctx, local_path, volume_id, remote_path, chunk_size, no_resume):
    """Upload a file to a network volume."""
    try:
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)

        # Get volume ID if not provided
        if not volume_id:
            volumes = client.list_network_volumes()
            if not volumes:
                console.print("[yellow]No network volumes found.[/yellow]")
                return

            console.print("Available volumes:")
            for i, vol in enumerate(volumes):
                console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

            choice = Prompt.ask(
                "Select volume",
                choices=[str(i + 1) for i in range(len(volumes))],
                default="1",
            )
            volume_id = volumes[int(choice) - 1]["id"]

        # Set remote path if not provided
        if not remote_path:
            remote_path = Path(local_path).name

        # Get volume details
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Set up S3 client
        s3_client = setup_s3_client(datacenter_id, endpoint_url)

        # Upload file
        console.print(
            f"Uploading [cyan]{local_path}[/cyan] to [green]{volume_id}/{remote_path}[/green]"
        )
        enable_resume = not no_resume
        s3_client.upload_file(local_path, volume_id, remote_path, chunk_size, enable_resume)
        console.print("[green]✓[/green] Upload completed successfully!")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("volume_id", required=False)
@click.argument("remote_path", required=False)
@click.option(
    "--local-path", help="Local path to save file (default: same as remote filename)"
)
@click.pass_context
def download(ctx, volume_id, remote_path, local_path):
    """Download a file from a network volume."""
    try:
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)

        # Get volume ID if not provided
        if not volume_id:
            volumes = client.list_network_volumes()
            if not volumes:
                console.print("[yellow]No network volumes found.[/yellow]")
                return

            console.print("Available volumes:")
            for i, vol in enumerate(volumes):
                console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

            choice = Prompt.ask(
                "Select volume",
                choices=[str(i + 1) for i in range(len(volumes))],
                default="1",
            )
            volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Set up S3 client
        s3_client = setup_s3_client(datacenter_id, endpoint_url)

        # Get remote path if not provided
        if not remote_path:
            files = s3_client.list_files(volume_id)
            if not files:
                console.print("[yellow]No files found in volume.[/yellow]")
                return

            console.print("Available files:")
            for i, file_info in enumerate(files):
                size = file_info["size"]
                if size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                console.print(f"  {i+1}. {file_info['key']} ({size_str})")

            choice = Prompt.ask(
                "Select file",
                choices=[str(i + 1) for i in range(len(files))],
                default="1",
            )
            remote_path = files[int(choice) - 1]["key"]

        # Set local path if not provided
        if not local_path:
            local_path = Path(remote_path).name

        # Download file
        console.print(
            f"Downloading [cyan]{volume_id}/{remote_path}[/cyan] to [green]{local_path}[/green]"
        )
        s3_client.download_file(volume_id, remote_path, local_path)
        console.print("[green]✓[/green] Download completed successfully!")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Interactive mode for managing volumes and files."""
    try:
        # Get API key interactively if not provided and store it in context
        if not ctx.obj["api_key"]:
            api_key = get_api_key_interactively()
            ctx.obj["api_key"] = api_key  # Store for the session

        # Store S3 credentials in context for session persistence
        ctx.obj["s3_access_key"] = None
        ctx.obj["s3_secret_key"] = None

        client = RunpodClient(ctx.obj["api_key"])

        while True:
            console.print("\n[bold]Runpod Storage Manager[/bold]")
            console.print("1. List volumes")
            console.print("2. Create volume")
            console.print("3. Update volume")
            console.print("4. Delete volume")
            console.print("5. List files")
            console.print("6. Upload file/directory")
            console.print("7. Download file/directory")
            console.print("8. Browse volume files")
            console.print("9. Exit")

            choice = Prompt.ask(
                "Choose action",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
                default="1",
            )

            if choice == "1":
                # Call function directly instead of ctx.invoke to maintain context
                _interactive_list_volumes(ctx.obj["api_key"])
            elif choice == "2":
                name = Prompt.ask("Volume name")
                size = int(Prompt.ask("Size in GB", default="10"))
                datacenter = prompt_datacenter("Datacenter")
                _interactive_create_volume(ctx.obj["api_key"], name, size, datacenter)
            elif choice == "3":
                _interactive_update_volume(ctx.obj["api_key"])
            elif choice == "4":
                _interactive_delete_volume(ctx.obj["api_key"])
            elif choice == "5":
                _interactive_list_files(ctx.obj["api_key"], ctx.obj)
            elif choice == "6":
                local_path = Prompt.ask("Local file/directory path")
                if not Path(local_path).exists():
                    console.print("[red]Path not found![/red]")
                    continue
                _interactive_upload(ctx.obj["api_key"], local_path, ctx.obj)
            elif choice == "7":
                _interactive_download(ctx.obj["api_key"], ctx.obj)
            elif choice == "8":
                _interactive_browse_files(ctx.obj["api_key"], ctx.obj)
            elif choice == "9":
                console.print("Goodbye!")
                break

    except KeyboardInterrupt:
        console.print("\nGoodbye!")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def get_s3_credentials_for_session(session_ctx):
    """Get S3 credentials and store them in session context."""
    # Check if already stored in session
    if session_ctx["s3_access_key"] and session_ctx["s3_secret_key"]:
        return session_ctx["s3_access_key"], session_ctx["s3_secret_key"]

    # Check environment variables first
    access_key = os.getenv("RUNPOD_S3_ACCESS_KEY")
    secret_key = os.getenv("RUNPOD_S3_SECRET_KEY")

    if not access_key or not secret_key:
        console.print(
            "\n[yellow]For file operations, you'll need S3 API credentials.[/yellow]"
        )
        console.print(
            "Get them from: [link]https://console.runpod.io/user/settings[/link] → S3 API Keys\n"
        )

        if not access_key:
            access_key = Prompt.ask("S3 Access Key (user_...)")

        if not secret_key:
            secret_key = Prompt.ask("S3 Secret Key (rps_...)", password=True)

    # Store in session context
    session_ctx["s3_access_key"] = access_key
    session_ctx["s3_secret_key"] = secret_key

    return access_key, secret_key


def _interactive_list_volumes(api_key):
    """Internal function to list volumes without re-prompting for API key."""
    try:
        client = RunpodClient(api_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching network volumes...", total=None)
            volumes = client.list_network_volumes()
            progress.update(task, completed=1)

        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            console.print("Create one with option 2 (Create volume)")
            return

        # Create a nice table
        table = Table(title="Network Volumes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Size (GB)", justify="right")
        table.add_column("Datacenter", style="blue")

        for volume in volumes:
            table.add_row(
                volume.get("id", "N/A"),
                volume.get("name", "N/A"),
                str(volume.get("size", "N/A")),
                volume.get("dataCenterId", "N/A"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_create_volume(api_key, name, size, datacenter):
    """Internal function to create volume without re-prompting for API key."""
    try:
        client = RunpodClient(api_key)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating network volume...", total=None)
            normalized_datacenter = RunpodClient.normalize_datacenter(datacenter)
            volume = client.create_network_volume(name, size, normalized_datacenter)
            progress.update(task, completed=1)

        console.print("[green]✓[/green] Created network volume:")
        console.print(f"  ID: {volume['id']}")
        console.print(f"  Name: {volume['name']}")
        console.print(f"  Size: {volume['size']} GB")
        console.print(f"  Datacenter: {volume['dataCenterId']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_update_volume(api_key):
    """Internal function to update volume without re-prompting for API key."""
    try:
        client = RunpodClient(api_key)

        # Get list of volumes
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(
                f"  {i+1}. {vol['id']} ({vol.get('name', 'Unnamed')}) - {vol.get('size', 'Unknown')} GB"
            )

        choice = Prompt.ask(
            "Select volume to update",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_to_update = volumes[int(choice) - 1]

        # Show current volume details
        console.print("\n[bold]Current volume details:[/bold]")
        console.print(f"  ID: {volume_to_update['id']}")
        console.print(f"  Name: {volume_to_update.get('name', 'Unnamed')}")
        console.print(f"  Size: {volume_to_update.get('size', 'Unknown')} GB")
        console.print(
            f"  Datacenter: {volume_to_update.get('dataCenterId', 'Unknown')}"
        )

        # Ask what to update
        console.print("\n[bold]What would you like to update?[/bold]")
        console.print("1. Name only")
        console.print("2. Size only (expand)")
        console.print("3. Both name and size")

        update_choice = Prompt.ask(
            "Choose update type", choices=["1", "2", "3"], default="1"
        )

        new_name = None
        new_size = None

        if update_choice in ["1", "3"]:
            current_name = volume_to_update.get("name", "Unnamed")
            new_name = Prompt.ask("New volume name", default=current_name)
            if new_name == current_name:
                new_name = None  # No change

        if update_choice in ["2", "3"]:
            current_size = volume_to_update.get("size", 0)
            console.print(
                "\n[yellow]⚠️  Note: Size can only be increased, not decreased![/yellow]"
            )
            console.print(f"Current size: {current_size} GB")

            while True:
                try:
                    new_size_input = Prompt.ask(
                        f"New size in GB (minimum {current_size + 1})"
                    )
                    new_size = int(new_size_input)

                    if new_size <= current_size:
                        console.print(
                            f"[red]Error: New size ({new_size} GB) must be larger than current size ({current_size} GB)[/red]"
                        )
                        continue

                    if new_size > 4000:
                        console.print(
                            "[red]Error: Maximum volume size is 4000 GB[/red]"
                        )
                        continue

                    break
                except ValueError:
                    console.print("[red]Error: Please enter a valid number[/red]")

        # Show update summary
        if new_name is None and new_size is None:
            console.print("[yellow]No changes to apply.[/yellow]")
            return

        console.print("\n[bold]Update summary:[/bold]")
        if new_name:
            console.print(
                f"  Name: {volume_to_update.get('name', 'Unnamed')} → {new_name}"
            )
        if new_size:
            console.print(
                f"  Size: {volume_to_update.get('size', 'Unknown')} GB → {new_size} GB"
            )

        # Confirm update
        if not Confirm.ask("\nProceed with update?", default=True):
            console.print("[yellow]Update cancelled.[/yellow]")
            return

        # Perform update
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating network volume...", total=None)
            updated_volume = client.update_network_volume(
                volume_to_update["id"], name=new_name, size=new_size
            )
            progress.update(task, completed=1)

        console.print("[green]✓[/green] Volume updated successfully:")
        console.print(f"  ID: {updated_volume['id']}")
        console.print(f"  Name: {updated_volume['name']}")
        console.print(f"  Size: {updated_volume['size']} GB")
        console.print(f"  Datacenter: {updated_volume['dataCenterId']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_delete_volume(api_key):
    """Internal function to delete volume without re-prompting for API key."""
    try:
        client = RunpodClient(api_key)

        # Get list of volumes
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(
                f"  {i+1}. {vol['id']} ({vol.get('name', 'Unnamed')}) - {vol.get('size', 'Unknown')} GB"
            )

        choice = Prompt.ask(
            "Select volume to delete",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_to_delete = volumes[int(choice) - 1]

        # Show volume details and get confirmation
        console.print(
            "\n[bold red]⚠️  WARNING: You are about to delete volume:[/bold red]"
        )
        console.print(f"  ID: {volume_to_delete['id']}")
        console.print(f"  Name: {volume_to_delete.get('name', 'Unnamed')}")
        console.print(f"  Size: {volume_to_delete.get('size', 'Unknown')} GB")
        console.print(
            f"  Datacenter: {volume_to_delete.get('dataCenterId', 'Unknown')}"
        )

        console.print("\n[bold red]🚨 This action is IRREVERSIBLE![/bold red]")
        console.print(
            "[red]All files and data in this volume will be permanently lost.[/red]"
        )

        # Double confirmation
        first_confirm = Confirm.ask(
            f"\nAre you sure you want to delete volume {volume_to_delete['id']}?",
            default=False,
        )

        if not first_confirm:
            console.print("[yellow]Volume deletion cancelled.[/yellow]")
            return

        # Type volume ID for final confirmation
        volume_id = volume_to_delete["id"]
        typed_id = Prompt.ask(
            f"\nTo confirm, please type the volume ID exactly: [bold]{volume_id}[/bold]"
        )

        if typed_id != volume_id:
            console.print("[red]Volume ID does not match. Deletion cancelled.[/red]")
            return

        # Delete the volume
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting network volume...", total=None)
            success = client.delete_network_volume(volume_id)
            progress.update(task, completed=1)

        if success:
            console.print(
                f"[green]✓[/green] Network volume {volume_id} deleted successfully."
            )
        else:
            console.print(
                f"[red]Failed to delete volume {volume_id}. It may not exist.[/red]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_list_files(api_key, session_ctx):
    """Internal function to list files without re-prompting for credentials."""
    try:
        client = RunpodClient(api_key)

        # Get volume ID
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

        choice = Prompt.ask(
            "Select volume",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details for datacenter info
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Get S3 credentials from session
        access_key, secret_key = get_s3_credentials_for_session(session_ctx)

        # Set up S3 client
        s3_client = RunpodS3Client(
            access_key=access_key,
            secret_key=secret_key,
            region=datacenter_id,
            endpoint_url=endpoint_url,
        )

        path = Prompt.ask("Remote path to list (default: root)", default="")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Listing files...", total=None)
            files = s3_client.list_files(volume_id, path)
            progress.update(task, completed=1)

        if not files:
            console.print(f"[yellow]No files found in volume {volume_id}[/yellow]")
            return

        # Create table
        table = Table(title=f"Files in {volume_id}/{path}")
        table.add_column("Path", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Last Modified", style="dim")

        for file_info in files:
            # Format size
            size = file_info["size"]
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"

            table.add_row(
                file_info["key"],
                size_str,
                file_info["last_modified"].strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_upload(api_key, local_path, session_ctx):
    """Internal function to upload file or directory without re-prompting for credentials."""
    try:
        client = RunpodClient(api_key)
        local_path = Path(local_path)

        # Get volume ID
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

        choice = Prompt.ask(
            "Select volume",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Get S3 credentials from session
        access_key, secret_key = get_s3_credentials_for_session(session_ctx)

        # Set up S3 client
        s3_client = RunpodS3Client(
            access_key=access_key,
            secret_key=secret_key,
            region=datacenter_id,
            endpoint_url=endpoint_url,
        )

        if local_path.is_file():
            # Single file upload
            remote_path = Prompt.ask("Remote path", default=local_path.name)
            console.print(
                f"Uploading file [cyan]{local_path}[/cyan] to [green]{volume_id}/{remote_path}[/green]"
            )
            s3_client.upload_file(str(local_path), volume_id, remote_path)
            console.print("[green]✓[/green] File upload completed successfully!")

        elif local_path.is_dir():
            # Directory upload
            remote_dir = Prompt.ask("Remote directory", default=local_path.name)

            # Ask about sync options
            delete_extra = Confirm.ask(
                "Delete remote files not present locally?", default=False
            )

            console.print(
                f"Syncing directory [cyan]{local_path}[/cyan] to [green]{volume_id}/{remote_dir}[/green]"
            )

            def progress_callback(current, total, filename):
                percent = (current / total) * 100
                console.print(
                    f"  [{current:3d}/{total:3d}] ({percent:5.1f}%) {filename}"
                )

            s3_client.upload_directory(
                str(local_path),
                volume_id,
                remote_dir,
                exclude_patterns=["*.DS_Store", "*.pyc", "__pycache__/*", ".git/*"],
                delete=delete_extra,
                progress_callback=progress_callback,
            )
            console.print("[green]✓[/green] Directory sync completed successfully!")
        else:
            console.print("[red]Path is neither a file nor a directory![/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_download(api_key, session_ctx):
    """Internal function to download file or directory without re-prompting for credentials."""
    try:
        client = RunpodClient(api_key)

        # Get volume ID
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

        choice = Prompt.ask(
            "Select volume",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Get S3 credentials from session
        access_key, secret_key = get_s3_credentials_for_session(session_ctx)

        # Set up S3 client
        s3_client = RunpodS3Client(
            access_key=access_key,
            secret_key=secret_key,
            region=datacenter_id,
            endpoint_url=endpoint_url,
        )

        # Ask what to download
        download_type = Prompt.ask(
            "Download type", choices=["file", "directory"], default="file"
        )

        if download_type == "file":
            # Single file download
            files = s3_client.list_files(volume_id)
            if not files:
                console.print("[yellow]No files found in volume.[/yellow]")
                return

            console.print("Available files:")
            for i, file_info in enumerate(files):
                size = file_info["size"]
                if size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                console.print(f"  {i+1}. {file_info['key']} ({size_str})")

            choice = Prompt.ask(
                "Select file",
                choices=[str(i + 1) for i in range(len(files))],
                default="1",
            )
            remote_path = files[int(choice) - 1]["key"]
            local_path = Prompt.ask("Local path", default=Path(remote_path).name)

            console.print(
                f"Downloading [cyan]{volume_id}/{remote_path}[/cyan] to [green]{local_path}[/green]"
            )
            s3_client.download_file(volume_id, remote_path, local_path)
            console.print("[green]✓[/green] File download completed successfully!")

        else:
            # Directory download
            remote_dir = Prompt.ask(
                "Remote directory path (leave empty for root)", default=""
            )
            local_dir = Prompt.ask("Local directory path")

            console.print(
                f"Downloading directory [cyan]{volume_id}/{remote_dir}[/cyan] to [green]{local_dir}[/green]"
            )

            def progress_callback(current, total, filename):
                percent = (current / total) * 100
                console.print(
                    f"  [{current:3d}/{total:3d}] ({percent:5.1f}%) {filename}"
                )

            s3_client.download_directory(
                volume_id, remote_dir, local_dir, progress_callback=progress_callback
            )
            console.print("[green]✓[/green] Directory download completed successfully!")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _interactive_browse_files(api_key, session_ctx):
    """Interactive file browser for exploring network volume files."""
    try:
        client = RunpodClient(api_key)

        # Get volume ID
        volumes = client.list_network_volumes()
        if not volumes:
            console.print("[yellow]No network volumes found.[/yellow]")
            return

        console.print("Available volumes:")
        for i, vol in enumerate(volumes):
            console.print(f"  {i+1}. {vol['id']} ({vol['name']})")

        choice = Prompt.ask(
            "Select volume",
            choices=[str(i + 1) for i in range(len(volumes))],
            default="1",
        )
        volume_id = volumes[int(choice) - 1]["id"]

        # Get volume details
        volume = client.get_network_volume(volume_id)
        datacenter_id = volume["dataCenterId"]
        endpoint_url = client.get_s3_endpoint(datacenter_id)

        # Get S3 credentials from session
        access_key, secret_key = get_s3_credentials_for_session(session_ctx)

        # Set up S3 client
        s3_client = RunpodS3Client(
            access_key=access_key,
            secret_key=secret_key,
            region=datacenter_id,
            endpoint_url=endpoint_url,
        )

        current_path = ""

        while True:
            console.print(f"\n[bold]File Browser - Volume: {volume_id}[/bold]")
            console.print(f"Current path: /{current_path}")

            # List files in current directory
            try:
                files = s3_client.list_files(volume_id, current_path)
            except Exception as e:
                console.print(f"[red]Error listing files: {e}[/red]")
                break

            if not files:
                console.print("[yellow]No files found in this directory.[/yellow]")
            else:
                # Group files by directory
                directories = set()
                file_list = []

                for file_info in files:
                    key = file_info["key"]
                    if current_path:
                        if not key.startswith(current_path):
                            continue
                        relative_key = key[len(current_path) :].lstrip("/")
                    else:
                        relative_key = key

                    if "/" in relative_key:
                        # This is in a subdirectory
                        dir_name = relative_key.split("/")[0]
                        directories.add(dir_name)
                    else:
                        # This is a file in current directory
                        file_list.append(file_info)

                # Display directories
                if directories:
                    console.print("\n[bold blue]Directories:[/bold blue]")
                    for i, dir_name in enumerate(sorted(directories), 1):
                        console.print(f"  📁 {dir_name}/")

                # Display files
                if file_list:
                    console.print("\n[bold green]Files:[/bold green]")
                    table = Table()
                    table.add_column("Name", style="cyan")
                    table.add_column("Size", justify="right")
                    table.add_column("Modified", style="dim")

                    for file_info in file_list:
                        key = file_info["key"]
                        if current_path:
                            display_name = key[len(current_path) :].lstrip("/")
                        else:
                            display_name = key

                        size = file_info["size"]
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        elif size < 1024 * 1024 * 1024:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        else:
                            size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"

                        table.add_row(
                            display_name,
                            size_str,
                            file_info["last_modified"].strftime("%Y-%m-%d %H:%M"),
                        )

                    console.print(table)

            # Navigation options
            console.print("\n[bold]Actions:[/bold]")
            console.print("1. Enter directory")
            console.print("2. Go up one level")
            console.print("3. Download file")
            console.print("4. Delete file")
            console.print("5. Exit browser")

            action = Prompt.ask(
                "Choose action", choices=["1", "2", "3", "4", "5"], default="5"
            )

            if action == "1":
                if directories:
                    dir_choices = sorted(directories)
                    console.print("Available directories:")
                    for i, dir_name in enumerate(dir_choices, 1):
                        console.print(f"  {i}. {dir_name}")

                    dir_choice = Prompt.ask(
                        "Select directory",
                        choices=[str(i) for i in range(1, len(dir_choices) + 1)],
                    )
                    selected_dir = dir_choices[int(dir_choice) - 1]
                    current_path = f"{current_path}/{selected_dir}".strip("/")
                else:
                    console.print("[yellow]No directories to enter.[/yellow]")

            elif action == "2":
                if current_path:
                    current_path = "/".join(current_path.split("/")[:-1])
                else:
                    console.print("[yellow]Already at root directory.[/yellow]")

            elif action == "3":
                if file_list:
                    console.print("Available files:")
                    for i, file_info in enumerate(file_list, 1):
                        key = file_info["key"]
                        if current_path:
                            display_name = key[len(current_path) :].lstrip("/")
                        else:
                            display_name = key
                        console.print(f"  {i}. {display_name}")

                    file_choice = Prompt.ask(
                        "Select file to download",
                        choices=[str(i) for i in range(1, len(file_list) + 1)],
                    )
                    selected_file = file_list[int(file_choice) - 1]

                    local_path = Prompt.ask(
                        "Local path", default=Path(selected_file["key"]).name
                    )
                    console.print(
                        f"Downloading [cyan]{selected_file['key']}[/cyan] to [green]{local_path}[/green]"
                    )
                    s3_client.download_file(volume_id, selected_file["key"], local_path)
                    console.print("[green]✓[/green] Download completed!")
                else:
                    console.print("[yellow]No files to download.[/yellow]")

            elif action == "4":
                if file_list:
                    console.print("Available files:")
                    for i, file_info in enumerate(file_list, 1):
                        key = file_info["key"]
                        if current_path:
                            display_name = key[len(current_path) :].lstrip("/")
                        else:
                            display_name = key
                        console.print(f"  {i}. {display_name}")

                    file_choice = Prompt.ask(
                        "Select file to delete",
                        choices=[str(i) for i in range(1, len(file_list) + 1)],
                    )
                    selected_file = file_list[int(file_choice) - 1]

                    if Confirm.ask(
                        f"Are you sure you want to delete {selected_file['key']}?"
                    ):
                        s3_client.delete_file(volume_id, selected_file["key"])
                        console.print(
                            f"[green]✓[/green] Deleted {selected_file['key']}"
                        )
                else:
                    console.print("[yellow]No files to delete.[/yellow]")

            elif action == "5":
                break

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def main():
    """Main entry point."""
    cli()

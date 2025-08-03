"""CLI interface for Runpod network storage management."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from tabulate import tabulate

from ..core.client import RunpodClient
from ..core.s3_client import RunpodS3Client


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
        endpoint_url=endpoint_url
    )


def get_api_key_interactively():
    """Prompt user for API key if not provided."""
    api_key = os.getenv("RUNPOD_API_KEY")
    
    if not api_key:
        console.print("\n[yellow]Welcome to Runpod Storage CLI![/yellow]")
        console.print("To get started, you'll need your Runpod API key.")
        console.print("Get it from: [link]https://console.runpod.io/user/settings[/link]\n")
        
        api_key = Prompt.ask("Please enter your Runpod API key", password=True)
        
        if Confirm.ask("Would you like to save this API key as an environment variable for future use?"):
            console.print("\nAdd this to your shell profile (~/.bashrc, ~/.zshrc, etc.):")
            console.print(f"[green]export RUNPOD_API_KEY=\"{api_key}\"[/green]")
            console.print(f"\nOr run: [green]echo 'export RUNPOD_API_KEY=\"{api_key}\"' >> ~/.bashrc[/green]")
            console.print("Then reload your shell: [green]source ~/.bashrc[/green]\n")
    
    return api_key


def get_s3_credentials_interactively():
    """Prompt user for S3 credentials if not provided."""
    access_key = os.getenv("RUNPOD_S3_ACCESS_KEY")
    secret_key = os.getenv("RUNPOD_S3_SECRET_KEY")
    
    if not access_key or not secret_key:
        console.print("\n[yellow]For file operations, you'll also need S3 API credentials.[/yellow]")
        console.print("Get them from: [link]https://console.runpod.io/user/settings[/link] → S3 API Keys\n")
        
        if not access_key:
            access_key = Prompt.ask("S3 Access Key (user_...)")
        
        if not secret_key:
            secret_key = Prompt.ask("S3 Secret Key (rps_...)", password=True)
        
        # Save to environment for this session
        os.environ["RUNPOD_S3_ACCESS_KEY"] = access_key
        os.environ["RUNPOD_S3_SECRET_KEY"] = secret_key
        
        if Confirm.ask("Would you like to save these S3 credentials as environment variables?"):
            console.print("\nAdd these to your shell profile:")
            console.print(f"[green]export RUNPOD_S3_ACCESS_KEY=\"{access_key}\"[/green]")
            console.print(f"[green]export RUNPOD_S3_SECRET_KEY=\"{secret_key}\"[/green]\n")
    
    return access_key, secret_key


@click.group()
@click.option(
    "--api-key",
    envvar="RUNPOD_API_KEY",
    help="Runpod API key (or set RUNPOD_API_KEY env var)"
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
                volume.get("dataCenterId", "N/A")
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
    type=click.Choice(list(RunpodClient.get_available_datacenters().keys())),
    help="Datacenter ID"
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
            datacenter = Prompt.ask(
                "Choose datacenter",
                choices=list(client.get_available_datacenters().keys()),
                default="EU-RO-1"
            )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating network volume...", total=None)
            volume = client.create_network_volume(name, size, datacenter)
            progress.update(task, completed=1)
        
        console.print(f"[green]✓[/green] Created network volume:")
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
                choices=[str(i+1) for i in range(len(volumes))],
                default="1"
            )
            volume_id = volumes[int(choice)-1]["id"]
        
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
                file_info["last_modified"].strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("local_path", type=click.Path(exists=True))
@click.argument("volume_id", required=False)
@click.option("--remote-path", help="Remote path (default: same as local filename)")
@click.option("--chunk-size", type=int, default=50*1024*1024, help="Chunk size for large files (default: 50MB)")
@click.pass_context
def upload(ctx, local_path, volume_id, remote_path, chunk_size):
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
                choices=[str(i+1) for i in range(len(volumes))],
                default="1"
            )
            volume_id = volumes[int(choice)-1]["id"]
        
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
        console.print(f"Uploading [cyan]{local_path}[/cyan] to [green]{volume_id}/{remote_path}[/green]")
        s3_client.upload_file(local_path, volume_id, remote_path, chunk_size)
        console.print("[green]✓[/green] Upload completed successfully!")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("volume_id", required=False)
@click.argument("remote_path", required=False)
@click.option("--local-path", help="Local path to save file (default: same as remote filename)")
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
                choices=[str(i+1) for i in range(len(volumes))],
                default="1"
            )
            volume_id = volumes[int(choice)-1]["id"]
        
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
                choices=[str(i+1) for i in range(len(files))],
                default="1"
            )
            remote_path = files[int(choice)-1]["key"]
        
        # Set local path if not provided
        if not local_path:
            local_path = Path(remote_path).name
        
        # Download file
        console.print(f"Downloading [cyan]{volume_id}/{remote_path}[/cyan] to [green]{local_path}[/green]")
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
        # Get API key interactively if not provided
        api_key = ctx.obj["api_key"] or get_api_key_interactively()
        client = RunpodClient(api_key)
        
        while True:
            console.print("\n[bold]Runpod Storage Manager[/bold]")
            console.print("1. List volumes")
            console.print("2. Create volume")
            console.print("3. List files")
            console.print("4. Upload file")
            console.print("5. Download file")
            console.print("6. Exit")
            
            choice = Prompt.ask(
                "Choose action",
                choices=["1", "2", "3", "4", "5", "6"],
                default="1"
            )
            
            if choice == "1":
                ctx.invoke(list_volumes)
            elif choice == "2":
                name = Prompt.ask("Volume name")
                size = int(Prompt.ask("Size in GB", default="10"))
                datacenter = Prompt.ask(
                    "Datacenter",
                    choices=list(client.get_available_datacenters().keys()),
                    default="EU-RO-1"
                )
                ctx.invoke(create_volume, name=name, size=size, datacenter=datacenter)
            elif choice == "3":
                ctx.invoke(list_files)
            elif choice == "4":
                local_path = Prompt.ask("Local file path")
                if not Path(local_path).exists():
                    console.print("[red]File not found![/red]")
                    continue
                ctx.invoke(upload, local_path=local_path, volume_id=None, remote_path=None, chunk_size=50*1024*1024)
            elif choice == "5":
                ctx.invoke(download, volume_id=None, remote_path=None, local_path=None)
            elif choice == "6":
                console.print("Goodbye!")
                break
            
    except KeyboardInterrupt:
        console.print("\nGoodbye!")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()
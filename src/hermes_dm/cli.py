import asyncio
import json

import typer

# Import our backend components
from hermes_dm.client.connection import HermesClient
from hermes_dm.client.connection import HermesError
from hermes_dm.daemon.server import PowerSupplyDaemon
from hermes_dm.monitor import main as monitor_main

# Create the main Typer application
app = typer.Typer(help="Hermes Device Manager: Control and log programmable lab instruments.", no_args_is_help=True)

# Create Sub-Command Groups
daemon_app = typer.Typer(help="Manage the background Hermes daemon.")
device_app = typer.Typer(help="Manage and configure connected devices.")

# Bind the sub-groups to the main app
app.add_typer(daemon_app, name="daemon")
app.add_typer(device_app, name="device")


# ==========================================
# 1. DAEMON COMMANDS (hermes daemon ...)
# ==========================================


@daemon_app.command("start")
def start_daemon(
    db_dir: str = typer.Option("./logs", help="Directory for SQLite databases"),
    cmd_port: int = typer.Option(5555, help="ZeroMQ REP port for commands"),
    pub_port: int = typer.Option(5556, help="ZeroMQ PUB port for telemetry"),
):
    """Start the background hardware management server."""
    typer.echo(f"Starting Hermes Daemon (Ports {cmd_port} & {pub_port})...")
    daemon = PowerSupplyDaemon(db_directory=db_dir, cmd_port=cmd_port, pub_port=pub_port)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        typer.echo("\nShutting down gracefully.")


@daemon_app.command("status")
def daemon_status(host: str = typer.Option("localhost", help="Daemon IP"), port: int = typer.Option(5555, help="Daemon command port")):
    """Check if the daemon is running and view active state."""
    try:
        with HermesClient(host, port) as client:
            status = client.get_status()
            # Pretty-print the JSON response
            typer.echo(json.dumps(status, indent=2))
    except Exception as e:
        typer.echo(f"Failed to reach daemon: {e}", err=True)


# ==========================================
# 2. DEVICE COMMANDS (hermes device ...)
# ==========================================


@device_app.command("scan")
def scan_devices(host: str = typer.Option("localhost", help="Daemon IP"), port: int = typer.Option(5555, help="Daemon command port")):
    """Scan the daemon's host machine for physical SCPI instruments."""
    typer.echo(f"Scanning for instruments on {host}:{port}...")
    try:
        with HermesClient(host, port) as client:
            resources = client.list_scpi_resources()

            if not resources:
                typer.secho("No SCPI resources found.", fg=typer.colors.YELLOW)
                return

            typer.secho("\nAvailable SCPI Resources:", fg=typer.colors.GREEN, bold=True)
            for res in resources:
                typer.echo(f"  - {res}")

    except Exception as e:
        typer.secho(f"Error communicating with daemon: {e}", fg=typer.colors.RED, err=True)


@device_app.command("connect")
def connect_device(
    name: str = typer.Argument(..., help="Short name (e.g., Main_PSU)"),
    model: str = typer.Argument(..., help="Driver model (e.g., Keithley2410)"),
    identifier: str = typer.Argument(..., help="PyVISA identifier"),
    host: str = typer.Option("localhost"),
    port: int = typer.Option(5555),
):
    """Connect a physical instrument to the running daemon."""
    try:
        with HermesClient(host, port) as client:
            result = client.connect_device(name, model, identifier)
            typer.secho(f"Success: {result}", fg=typer.colors.GREEN)
    except HermesError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)


@device_app.command("set-voltage")
def set_voltage(
    name: str = typer.Argument(..., help="Name of the connected device"),
    voltage: float = typer.Argument(..., help="Voltage level in Volts"),
    enable: bool = typer.Option(False, "--enable", help="Also enable the output"),
    host: str = typer.Option("localhost"),
    port: int = typer.Option(5555),
):
    """Set the voltage of a connected power supply."""
    settings = {"voltage_level": voltage}
    if enable:
        settings["output_enabled"] = True

    try:
        with HermesClient(host, port) as client:
            result = client.configure_device(name, settings)
            typer.secho(f"Success: {result}", fg=typer.colors.GREEN)
    except HermesError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)


# ==========================================
# 3. ROOT COMMANDS (hermes monitor)
# ==========================================
# For commands that shouldn't be buried in a subgroup, attach directly to `app`


@app.command("monitor")
def launch_monitor():
    """Launch the live telemetry monitor."""
    # We can just route this to the monitor logic we already built
    monitor_main()


# Standard execution block
def main():
    app()


if __name__ == "__main__":
    main()

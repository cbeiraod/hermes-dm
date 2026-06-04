import json
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import zmq


class HermesError(Exception):
    """Custom exception raised when the daemon returns an error."""

    pass


class HermesClient:
    """
    Synchronous client for communicating with the Hermes Device Manager daemon.
    """

    def __init__(self, host: str = "localhost", port: int = 5555, timeout_ms: int = 5000):
        self.host = host
        self.port = port

        # Initialize ZeroMQ context and Request (REQ) socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

        # Connect to the daemon
        self.socket.connect(f"tcp://{self.host}:{self.port}")

        # CRITICAL: Set a receive timeout.
        # If the daemon crashes, we don't want client scripts to hang forever waiting.
        self.socket.setsockopt(zmq.RCVTIMEO, timeout_ms)

    def _send_command(self, command: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Internal helper to package, send, and validate JSON commands."""
        if args is None:
            args = {}

        payload = {"command": command, "args": args}

        try:
            # 1. Send the JSON request
            self.socket.send_string(json.dumps(payload))

            # 2. Wait for the reply
            response_str = self.socket.recv_string()

        except zmq.error.Again as e:
            raise TimeoutError(f"No response from Hermes daemon at {self.host}:{self.port}. Is it running?") from e

        response = json.loads(response_str)

        # 3. Handle daemon-side errors cleanly
        if response.get("status") == "error":
            raise HermesError(response.get("message", "Unknown error occurred on daemon."))

        return response

    # ==========================================
    # User-Facing API Methods
    # ==========================================

    def list_devices(self) -> List[str]:
        """Get a list of available USB/Serial/Network instrument identifiers."""
        return self._send_command("list_devices").get("data", [])

    def list_scpi_resources(self) -> List[str]:
        """
        Ask the daemon to scan the local hardware bus and return a list
        of available PyVISA identifiers (e.g., COM ports, USB, GPIB).
        """
        return self._send_command("list_scpi_resources").get("data", [])

    def connect_device(self, name: str, identifier: str, model: str = "auto") -> str:
        """
        Connect a physical instrument to the daemon.
        If 'model' is omitted or set to 'auto', Hermes will attempt to automatically
        discover the device type and required SCPI terminators.
        """
        args = {"name": name, "model": model, "identifier": identifier}
        return self._send_command("connect_device", args).get("message", "")

    def configure_device(self, name: str, settings: Dict[str, Any]) -> str:
        """Apply a dictionary of configuration settings to a specific device."""
        args = {"name": name, "settings": settings}
        return self._send_command("configure_device", args).get("message", "")

    def set_db_file(self, filename: str) -> str:
        """Create or select the SQLite database file for logging."""
        return self._send_command("set_db_file", {"filename": filename}).get("message", "")

    def start_logging(self) -> str:
        """Tell the daemon to start continuous polling and logging."""
        return self._send_command("start_logging").get("message", "")

    def stop_logging(self) -> str:
        """Tell the daemon to stop polling instruments."""
        return self._send_command("stop_logging").get("message", "")

    def set_interval(self, name: str, interval: float) -> str:
        """Set the polling interval (in seconds) for a specific device."""
        args = {"name": name, "interval": interval}
        return self._send_command("set_interval", args).get("message", "")

    def get_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get the status of the daemon, or a specific device if 'name' is provided."""
        args = {"name": name} if name else {}
        return self._send_command("get_status", args).get("data", {})

    def enable_db_logging(self, name: str) -> str:
        """
        Enable saving this device's data to the SQLite database.
        Live telemetry over ZMQ is unaffected.
        """
        args = {"name": name, "enable": True}
        return self._send_command("set_db_logging", args).get("message", "")

    def disable_db_logging(self, name: str) -> str:
        """
        Stop saving this device's data to the SQLite database.
        Live telemetry over ZMQ will continue streaming.
        """
        args = {"name": name, "enable": False}
        return self._send_command("set_db_logging", args).get("message", "")

    def close(self):
        """Cleanly shut down the ZeroMQ socket connection."""
        self.socket.close()
        self.context.term()

    # Allow use as a context manager (with block)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

import asyncio
import inspect
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pyvisa
import zmq
import zmq.asyncio

from ..instruments import AVAILABLE_DRIVERS
from ..instruments import match_driver_to_idn
from ..instruments.discovery import auto_discover_instrument

# Import our separated modules
from .db import DatabaseManager


class PowerSupplyDaemon:
    def __init__(self, db_directory: str, cmd_port: int = 5555, pub_port: int = 5556):
        self.cmd_port = cmd_port
        self.pub_port = pub_port

        # 1. Instantiate Managers ONCE
        self.db = DatabaseManager(db_directory)
        self.visa_rm = pyvisa.ResourceManager()

        # 2. State tracking
        self.connected_devices = {}
        self.logging_tasks = {}
        self.is_logging = False

        # 3. ZeroMQ setup
        self.ctx = zmq.asyncio.Context()
        self.cmd_socket = self.ctx.socket(zmq.REP)
        self.cmd_socket.bind(f"tcp://*:{self.cmd_port}")
        self.pub_socket = self.ctx.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.pub_port}")

        # Device Registry
        self.AVAILABLE_DRIVERS = AVAILABLE_DRIVERS
        # {
        #    "Keithley2410": Keithley2410,
        # }

        # Create the single, global thread for all GPIB communication
        self.shared_gpib_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Global_GPIB_Bus")

        self._routes = {
            "list_devices": self.list_devices,
            "list_scpi_resources": self.list_scpi_resources,
            "connect_device": self.connect_device,
            "disconnect_device": self.disconnect_device,
            "configure_device": self.configure_device,
            "get_status": self.get_status,
            "set_interval": self.set_interval,
            # "set_output": self.set_output,
            # "read_data": self.read_data,
            # "query_error": self.query_error,
            # "beep": self.beep,
            # "identify": self.identify,
            # "reset": self.reset,
            "set_db_logging": self.set_db_logging,
            "set_db_file": self.set_db_file,
            "start_logging": self.start_logging,
            "stop_logging": self.stop_logging,
        }

    async def start(self):
        """Main event loop for the daemon."""
        print(f"Daemon started. Command Port: {self.cmd_port}, Pub Port: {self.pub_port}")

        while True:
            # Wait for a command from a client
            message = await self.cmd_socket.recv_string()

            try:
                # Expecting commands as JSON: {"command": "list_devices", "args": {}}
                request = json.loads(message)
                command = request.get("command")
                args = request.get("args", {})

                # Route the command
                response = await self.handle_command(command, args)

            except Exception as e:
                response = {"status": "error", "message": str(e)}

            # Send the reply back to the client
            await self.cmd_socket.send_string(json.dumps(response))

    async def stop(self):
        """Cleanly shuts down the daemon, disconnects hardware, and releases network ports."""
        print("Initiating daemon shutdown...")

        # 1. Stop all background polling tasks
        self.stop_logging({})

        # 2. Disconnect all instruments gracefully
        # We cast the keys to a list because disconnect_device uses .pop(),
        # which would throw a "dictionary changed size during iteration" error otherwise.
        device_names = list(self.connected_devices.keys())
        for name in device_names:
            await self.disconnect_device({"name": name})

        # 3. Shut down the shared thread pool so it doesn't leave zombie threads
        self.shared_gpib_executor.shutdown(wait=True)

        # 4. Close the PyVISA Resource Manager
        if hasattr(self.visa_rm, "close"):
            self.visa_rm.close()

        # 5. Close the SQLite Database (Assuming your DatabaseManager has a close method.
        # If not, you might want to add a quick self.conn.close() to your db.py)
        if hasattr(self.db, "close"):
            self.db.close()

        # 6. Destroy the ZeroMQ Sockets and Context
        # Linger=0 tells ZMQ to drop any unsent messages immediately rather than hanging forever.
        self.cmd_socket.close(linger=0)
        self.pub_socket.close(linger=0)
        self.ctx.term()

        print("Daemon shutdown complete.")

    def list_devices(self, args: dict) -> dict:
        return {"status": "success", "data": {name: inst.identifier for name, inst in self.connected_devices.items()}}

    async def list_scpi_resources(self, args: dict) -> dict:
        try:
            # Offload the blocking OS-level scan to a background thread!
            # Using asyncio.to_thread() (Python 3.9+) prevents the daemon loop from freezing.
            resources = await asyncio.to_thread(self.visa_rm.list_resources)

            return {"status": "success", "data": list(resources)}
        except Exception as e:
            return {"status": "error", "message": f"Failed to scan resources: {e}"}

    async def connect_device(self, args: dict) -> dict:
        identifier = args.get("identifier")
        name = args.get("name", identifier)
        model = args.get("model")

        try:
            found_w_term = None
            found_r_term = None

            # AUTO-DISCOVERY TRIGGER
            if not model or model.lower() == "auto":
                # Run the blocking sweep in the default thread pool
                idn, found_w_term, found_r_term = await asyncio.to_thread(auto_discover_instrument, self.visa_rm, identifier)

                # Match the IDN string to a driver name
                model = match_driver_to_idn(idn)
                print(f"Auto-discovered {model} at {identifier}")

            if model not in AVAILABLE_DRIVERS:
                return {"status": "error", "message": f"Unknown model: {model}"}

            # Instantiate the correct class
            instrument = AVAILABLE_DRIVERS[model](
                name=name,
                identifier=identifier,
                visa_rm=self.visa_rm,
                gpib_executor=self.shared_gpib_executor,
            )

            # If auto-discovery found weird terminators, apply them to the new instance!
            if found_w_term is not None:
                instrument.config["write_termination"] = found_w_term
                instrument.config["read_termination"] = found_r_term

            await instrument.connect()

            self.connected_devices[name] = instrument
            if self.is_logging:
                self.logging_tasks[name] = asyncio.create_task(self._poll_device(name))
            return {"status": "success", "message": f"Connected {name} ({model})"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def disconnect_device(self, args: dict) -> dict:
        name = args.get("name")

        if not name:
            return {"status": "error", "message": "Missing 'name' argument in disconnect command."}

        if name not in self.connected_devices:
            return {"status": "error", "message": f"Device '{name}' is not currently connected."}

        try:
            # 1. Stop the background polling/logging task first
            if name in self.logging_tasks:
                polling_task = self.logging_tasks.pop(name)
                polling_task.cancel()

                # Optional but recommended: Suppress the expected CancelledError
                try:
                    await polling_task
                except asyncio.CancelledError:
                    pass

            # 2. Pop the instrument from the active dictionary so it can't be routed to anymore
            instrument = self.connected_devices.pop(name)

            # 3. Disconnect the hardware (assuming your driver has a disconnect method)
            if hasattr(instrument, "disconnect"):
                # If your connect() is async, your disconnect() should ideally be async too
                await instrument.disconnect()
            elif hasattr(instrument, "close"):
                # Fallback just in case you are exposing raw PyVISA connections
                await asyncio.to_thread(instrument.close)

            return {"status": "success", "message": f"Disconnected '{name}' successfully."}

        except Exception as e:
            # We use Exception here (not a bare except) to satisfy Ruff,
            # and because we want to catch hardware connection drops.
            return {"status": "error", "message": f"Error during disconnect: {str(e)}"}

    async def configure_device(self, args: dict) -> dict:
        name = args.get("name")
        settings = args.get("settings", {})

        if not name:
            return {"status": "error", "message": "Missing 'name' argument in configure command."}

        if name not in self.connected_devices:
            return {"status": "error", "message": f"Device '{name}' is not currently connected."}

        try:
            # Retrieve the instrument
            instrument = self.connected_devices[name]

            # Apply the configuration
            await instrument.configure(settings)

            return {"status": "success", "message": f"Configuration applied to '{name}'."}

        except Exception as e:
            return {"status": "error", "message": f"Error during configuration: {str(e)}"}

    def get_status(self, args: dict) -> dict:
        target_name = args.get("name")  # Optional

        if target_name:
            if target_name not in self.connected_devices:
                return {"status": "error", "message": "Device not found."}
            data = self.connected_devices[target_name].get_status()
        else:
            data = {
                "daemon_logging": self.is_logging,
                "devices": {name: inst.get_status() for name, inst in self.connected_devices.items()},
            }
        return {"status": "success", "data": data}

    def set_interval(self, args: dict) -> dict:
        name = args.get("name")
        new_interval = args.get("interval")

        if not isinstance(new_interval, (int, float)) or new_interval <= 0:
            return {"status": "error", "message": "Interval must be a positive number."}
        if not name:
            return {"status": "error", "message": "Missing 'name' argument in set_interval command."}
        if name not in self.connected_devices:
            return {"status": "error", "message": f"Device '{name}' is not currently connected."}

        self.connected_devices[name].poll_interval = new_interval
        return {"status": "success", "message": f"Interval for {name} set to {new_interval}s"}

    def set_db_logging(self, args: dict) -> dict:
        name = args.get("name")
        enable = args.get("enable")

        if not isinstance(enable, bool):
            return {"status": "error", "message": "Enable must be a boolean."}
        if not name:
            return {"status": "error", "message": "Missing 'name' argument in set_db_logging command."}
        if name not in self.connected_devices:
            return {"status": "error", "message": f"Device '{name}' is not currently connected."}

        if enable:
            self.connected_devices[name].enable_db_logging()
        else:
            self.connected_devices[name].disable_db_logging()
        action_str = "enabled" if enable else "disabled"
        return {"status": "success", "message": f"Database logging {action_str} for {name}"}

    def set_db_file(self, args: dict) -> dict:
        filename = args.get("filename")

        if not filename:
            return {"status": "error", "message": "Missing 'filename' argument in set_db_file command."}

        success = self.db.set_file(filename)
        if success:
            return {"status": "success", "message": "Database created."}
        return {"status": "error", "message": "File already exists."}

    def start_logging(self, args: dict) -> dict:
        self.is_logging = True
        # Spawn polling tasks for all connected devices
        for name in self.connected_devices:
            if name not in self.logging_tasks:
                self.logging_tasks[name] = asyncio.create_task(self._poll_device(name))
        return {"status": "success", "message": "Logging started."}

    def stop_logging(self, args: dict) -> dict:
        self.is_logging = False
        for task in self.logging_tasks.values():
            task.cancel()
        self.logging_tasks.clear()
        return {"status": "success", "message": "Logging stopped."}

    async def handle_command(self, command: str, payload: dict) -> dict:
        handler = self._routes.get(command)

        if not handler:
            return {"status": "error", "message": f"Unknown command: {command}"}

        # Execute the function
        result = handler(payload)

        # If the function was an 'async def', we must await the coroutine!
        if inspect.isawaitable(result):
            result = await result

        # Return the final resolved dictionary
        return result

    async def _poll_device(self, device_name: str):
        """Background task that runs continuously for a specific device."""
        instrument = self.connected_devices[device_name]

        while self.is_logging:
            start_time = time.monotonic()  # Track exact start time

            try:
                # 1. Fetch hardware readings
                readings = await instrument.read()
                timestamp = datetime.now().isoformat()

                for channel, metric, value in readings:
                    # 2. ALWAYS Publish to ZeroMQ
                    pub_data = {"device": device_name, "timestamp": timestamp, "channel": channel, "metric": metric, "value": value}
                    await self.pub_socket.send_string(f"DATA.{device_name}.{metric.upper()} {json.dumps(pub_data)}")

                    # 3. ONLY Log to Database if the device flag is True
                    if instrument.db_logging_enabled and self.db.conn is not None:
                        # (Assuming this SQLite call is fast enough not to need to_thread)
                        self.db.insert_reading(timestamp, device_name, channel, metric, value)

                # Calculate how long the hardware read actually took
                elapsed_time = time.monotonic() - start_time
                sleep_time = max(0.0, instrument.poll_interval - elapsed_time)

                # 4. Sleep inside the try block
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                # The stop_logging command was issued, break the loop cleanly
                break
            except Exception as e:
                # Log the error, but don't break the loop.
                # (e.g. if the instrument glitches, we want to try again next interval)
                logging.error(f"Error polling {device_name}: {e}")

                # Sleep briefly on error to prevent CPU-pegging infinite crash loops
                await asyncio.sleep(1.0)

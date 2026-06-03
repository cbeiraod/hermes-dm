import asyncio
import zmq
import zmq.asyncio
import json
import pyvisa
import time
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor

# Import our separated modules
from .db import DatabaseManager
from ..instruments.keithley2410 import Keithley2410
from ..instruments.discovery import auto_discover_instrument
from ..instruments import AVAILABLE_DRIVERS, match_driver_to_idn

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
        #{
        #    "Keithley2410": Keithley2410,
        #}
        
        # Create the single, global thread for all GPIB communication
        self.shared_gpib_executor = ThreadPoolExecutor(
            max_workers=1, 
            thread_name_prefix="Global_GPIB_Bus"
        )

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

    async def handle_command(self, command: str, args: dict) -> dict:
        """Command Router."""

        if command == "list_devices":
            return {"status": "success", "data": {name: inst.identifier for name, inst in self.connected_devices.items()}}

        elif command == "list_scpi_resources":
            try:
                # Offload the blocking OS-level scan to a background thread!
                # Using asyncio.to_thread() (Python 3.9+) prevents the daemon loop from freezing.
                resources = await asyncio.to_thread(self.visa_rm.list_resources)
                
                return {"status": "success", "data": list(resources)}
            except Exception as e:
                return {"status": "error", "message": f"Failed to scan resources: {e}"}

        elif command == "connect_device":
            identifier = args.get("identifier")
            name = args.get("name", identifier)
            model = args.get("model")
            
            try:
                found_w_term = None
                found_r_term = None
                
                # AUTO-DISCOVERY TRIGGER
                if not model or model.lower() == "auto":
                    # Run the blocking sweep in the default thread pool
                    loop = asyncio.get_running_loop()
                    idn, found_w_term, found_r_term = await loop.run_in_executor(
                        None, auto_discover_instrument, self.visa_rm, identifier
                    )
                    
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
                if self.is_logging == True:
                    self.logging_tasks[name] = asyncio.create_task(self._poll_device(name))
                return {"status": "success", "message": f"Connected {name} ({model})"}
                
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif command == "configure_device":
            name = args.get("name")
            settings = args.get("settings", {})
            if name not in self.connected_devices:
                return {"status": "error", "message": "Device not found."}
                
            try:
                await self.connected_devices[name].configure(settings)
                return {"status": "success", "message": "Configuration applied."}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif command == "get_status":
            target_name = args.get("name") # Optional
            
            if target_name:
                if target_name not in self.connected_devices:
                    return {"status": "error", "message": "Device not found."}
                data = self.connected_devices[target_name].get_status()
            else:
                data = {
                    "daemon_logging": self.is_logging,
                    "devices": {name: inst.get_status() for name, inst in self.connected_devices.items()}
                }
            return {"status": "success", "data": data}

        elif command == "set_interval":
            name = args.get("name")
            new_interval = args.get("interval")

            if not isinstance(new_interval, (int, float)) or new_interval <= 0:
                 return {"status": "error", "message": "Interval must be a positive number."}
            if name not in self.connected_devices:
                return {"status": "error", "message": "Device not found."}
                 
            self.connected_devices[name].poll_interval = new_interval
            return {"status": "success", "message": f"Interval for {name} set to {new_interval}s"}
        
        elif command == "set_db_logging":
            name = args.get("name")
            enable = args.get("enable")
            
            if name not in self.connected_devices:
                return {"status": "error", "message": "Device not found."}
                
            instrument = self.connected_devices[name]
            
            if enable:
                instrument.enable_db_logging()
                return {"status": "success", "message": f"Database logging enabled for {name}."}
            else:
                instrument.disable_db_logging()
                return {"status": "success", "message": f"Database logging disabled for {name}."}

        elif command == "set_db_file":
            success = self.db.set_file(args.get("filename"))
            if success:
                return {"status": "success", "message": "Database created."}
            return {"status": "error", "message": "File already exists."}
            
        elif command == "start_logging":
            self.is_logging = True
            # Spawn polling tasks for all connected devices
            for name in self.connected_devices:
                if name not in self.logging_tasks:
                    self.logging_tasks[name] = asyncio.create_task(self._poll_device(name))
            return {"status": "success", "message": "Logging started."}
            
        elif command == "stop_logging":
            self.is_logging = False
            for task in self.logging_tasks.values():
                task.cancel()
            self.logging_tasks.clear()
            return {"status": "success", "message": "Logging stopped."}
            
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    async def _poll_device(self, device_name: str):
        """Background task that runs continuously for a specific device."""
        instrument = self.connected_devices[device_name]
        
        while self.is_logging:
            start_time = time.monotonic() # Track exact start time
            
            try:
                readings = await instrument.read()
                timestamp = datetime.now().isoformat()
                
                for channel, metric, value in readings:
                    # 1. ALWAYS Publish to ZeroMQ
                    pub_data = {"device": device_name, "timestamp": timestamp, "channel": channel, "metric": metric, "value": value}
                    await self.pub_socket.send_string(f"DATA.{device_name}.{metric.upper()} {json.dumps(pub_data)}")
                    
                    # 2. ONLY Log to Database if the device flag is True
                    if instrument.db_logging_enabled and self.db.conn is not None:
                        self.db.insert_reading(timestamp, device_name, channel, metric, value)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error polling {device_name}: {e}")
                
            # Calculate how long the hardware read actually took
            elapsed_time = time.monotonic() - start_time
            
            # Sleep only for the REMAINING time in the interval. 
            # If elapsed_time > poll_interval, sleep_time becomes 0.
            sleep_time = max(0.0, instrument.poll_interval - elapsed_time)
            await asyncio.sleep(sleep_time)

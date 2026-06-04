import asyncio
from abc import ABC
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple


class BaseInstrument(ABC):
    """Base interface for all power supplies and measurement devices."""

    def __init__(self, name: str, identifier: str, **kwargs):
        self.name = name
        self.identifier = identifier
        self.is_connected = False
        self.db_logging_enabled = True
        self.config: Dict[str, Any] = {}
        self.poll_interval = 1.0

        # Safely extract injected resources
        self.visa_rm = kwargs.get("visa_rm")
        # self.modbus_rm = kwargs.get("modbus_rm") # For future expansion

        # Safely extract optional termination characters
        self.read_termination = kwargs.get("read_termination", "\n")
        self.write_termination = kwargs.get("write_termination", "\n")

        # 1. Look for the injected global GPIB executor
        shared_gpib_executor = kwargs.get("gpib_executor")

        # 2. Decide which thread pool to use based on the PyVISA identifier string
        if "GPIB" in self.identifier.upper() and shared_gpib_executor is not None:
            self._executor = shared_gpib_executor
        else:
            # USB, Serial, TCPIP, etc. get their own private thread
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"HW_Thread_{self.name}")

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    @abstractmethod
    async def connect(self):
        """Establish connection to the hardware."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Safely close the connection."""
        pass

    def enable_db_logging(self):
        """Enable saving this device's data to the SQLite database."""
        self.db_logging_enabled = True

    def disable_db_logging(self):
        """Disable saving this device's data to the SQLite database."""
        self.db_logging_enabled = False

    @abstractmethod
    async def configure(self, settings: Dict[str, Any]):
        """Parse dictionary, validate, and apply settings via SCPI."""
        pass

    @abstractmethod
    async def read(self) -> List[Tuple[int, str, float]]:
        """
        Poll the device.
        Returns a list of tuples: (channel_number, metric_name, value)
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return the current state and configuration of the device."""
        return {
            "name": self.name,
            "identifier": self.identifier,
            "connected": self.is_connected,
            "logging_enabled": self.is_logging,
            "poll_interval": self.poll_interval,
            "config": self.config,
        }

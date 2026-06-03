import pyvisa
import asyncio
from typing import Dict, Any, List, Tuple
from .base import BaseInstrument

class Keithley2410(BaseInstrument):
    """Driver for the Keithley 2410 SourceMeter."""
    
    def __init__(self, name: str, identifier: str, **kwargs):
        super().__init__(name, identifier, **kwargs)
        self.rm = self.visa_rm 
        self.instrument = None

    async def connect(self):
        if not self.rm:
            raise RuntimeError("No VISA ResourceManager provided.")
            
        try:
            self.instrument = await self._run_sync(self.rm.open_resource, self.identifier)

            if "read_termination" in self.config:
                self.read_termination = self.config["read_termination"]
            if "write_termination" in self.config:
                self.write_termination = self.config["write_termination"]
            
            self.instrument.timeout = 2000
            self.instrument.read_termination = self.read_termination
            self.instrument.write_termination = self.write_termination
            
            self.is_connected = True
            self.config = {"source_mode": "VOLT", "output_enabled": False}
            
            await self._run_sync(self.instrument.write, "*RST")
            
        except pyvisa.VisaIOError as e:
            raise ConnectionError(f"Failed to connect to {self.identifier}: {e}")

    async def disconnect(self):
        if self.is_connected and self.instrument:
            await self._run_sync(self.instrument.close)
            self.is_connected = False

    async def configure(self, settings: Dict[str, Any]):
        if not self.is_connected:
            raise RuntimeError("Not connected.")

        for key, value in settings.items():
            if key == "source_mode":
                if value not in ["VOLT", "CURR"]:
                    raise ValueError(f"Invalid source_mode: {value}. Must be VOLT or CURR.")
                await self._run_sync(self.instrument.write, f":SOUR:FUNC {value}")
                self.config["source_mode"] = value
                
            elif key == "compliance_current":
                if not (0.0001 <= value <= 1.05):
                    raise ValueError("Compliance current out of range (0.1mA to 1.05A).")
                await self._run_sync(self.instrument.write, f":SENS:CURR:DC:COMP {value}")
                self.config["compliance_current"] = value
                
            elif key == "output_enabled":
                scpi_val = "ON" if value else "OFF"
                await self._run_sync(self.instrument.write, f":OUTP {scpi_val}")
                self.config["output_enabled"] = bool(value)
                
            else:
                raise KeyError(f"Unknown configuration parameter for Keithley 2410: {key}")

    async def read(self) -> List[Tuple[int, str, float]]:
        if not self.is_connected or not self.config.get("output_enabled"):
            return []
            
        try:
            raw_response = await self._run_sync(self.instrument.query, ":READ?")
            values = [float(v) for v in raw_response.split(",")]
            
            return [
                (1, "Voltage", values[0]),
                (1, "Current", values[1])
            ]
        except (pyvisa.VisaIOError, ValueError, IndexError) as e:
             print(f"Read error on {self.name}: {e}")
             return []
from .base import BaseInstrument
from .keithley2410 import Keithley2410

# A convenient dictionary we can import into the Daemon
AVAILABLE_DRIVERS = {
    "Keithley2410": Keithley2410,
}

AUTO_DISCOVERY_MAP = {"2410": "Keithley2410", "KEITHLEY INSTRUMENTS INC.,MODEL 2410": "Keithley2410"}


def match_driver_to_idn(idn_string: str) -> str:
    """Finds the correct driver model name based on the IDN string."""
    for substring, model_name in AUTO_DISCOVERY_MAP.items():
        if substring in idn_string:
            return model_name
    raise ValueError(f"Unrecognized instrument IDN: {idn_string}")


__all__ = ["BaseInstrument", "Keithley2410", "AVAILABLE_DRIVERS", "match_driver_to_idn"]

__version__ = "0.1.0"

# Expose the client tools to the top level
from .client.connection import HermesClient, HermesError
from .client.telemetry import HermesTelemetryListener

# This restricts what gets imported if a user does `from hermes_dm import *`
__all__ = ["HermesClient", "HermesError", "HermesTelemetryListener", "__version__"]
__version__ = "0.0.1"

# Expose the client tools to the top level
from .client.connection import HermesClient
from .client.connection import HermesError
from .client.telemetry import HermesTelemetryListener

# This restricts what gets imported if a user does `from hermes_dm import *`
__all__ = ["HermesClient", "HermesError", "HermesTelemetryListener", "__version__"]

# Hermes Device Manager (`hermes-dm`)

[![PyPI version](https://img.shields.io/pypi/v/hermes-dm.svg)](https://pypi.org/project/hermes-dm/)
[![License: Zlib](https://img.shields.io/badge/License-Zlib-lightgrey.svg)](https://opensource.org/licenses/Zlib)

**Hermes** is a lightweight, high-performance, and asynchronous device manager designed to bridge the gap between classic test/measurement hardware and modern software architectures. 

By leveraging **ZeroMQ (ZMQ)** for swift, non-blocking message passing and **SCPI** (Standard Commands for Programmable Instruments) for hardware communication, Hermes allows you to seamlessly control, monitor, and log data from generic lab instruments.

---

## Features

* **Asynchronous Architecture:** Built on top of ZeroMQ for high-throughput, low-latency telemetry logging.
* **Generic SCPI Support:** Easily extensible to any programmable instrument (Power supplies, Oscilloscopes, DMMs, etc.).
* **Decoupled Logging:** Devices stream data asynchronously, isolating measurement constraints from data storage layers.
* **Lightweight Footprint:** Avoids heavy industrial middleware framework bloat.

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│ BACKGROUND DAEMON (hermes-daemon)                           │
│                                                             │
│  [ SCPI Instruments ] ◄──── (PyVISA) ────► [ Async Server ] │
│                                                 │     │     │
│  [ SQLite DB Logs ] ◄────── (Database) ─────────┘     │     │
└───────────────────────────────────────────────────────┼─────┘
                                                        │
                      (ZeroMQ: Ports 5555 REP & 5556 PUB)
                                                        │
┌───────────────────────────────────────────────────────▼─────┐
│ USER ENVIRONMENT (hermes_dm.client)                         │
│                                                             │
│  [ HermesClient Library ]                                   │
│            │                                                │
│            ▼                                                │
│  [ Standalone Scripts | Jupyter Notebooks | GUI App ]       │
└─────────────────────────────────────────────────────────────┘
```


## Installation

```bash
pip install hermes-dm
```

## Quick Start

Hermes operates on a robust Client-Server architecture to ensure your hardware polling never blocks your user interfaces or scripts.

### 1. Start the Background Daemon
Run this in your terminal to start the background hardware manager:

```bash
hermes-daemon --db-dir ./lab_data --cmd-port 5555
```

### 2. Control via Python Script
In a separate terminal, Jupyter notebook, or GUI, use the client library to issue commands to the daemon:

```python
from hermes_dm.client import HermesClient

# Connect to the background daemon
client = HermesClient(host="localhost", port=5555)

# Connect the hardware (driver logic is handled by the daemon)
client.connect_device(
    name="Main_PSU",
    model="Keithley2410",
    identifier="TCPIP::111.222.33.44::INSTR"
)

# Configure the instrument
client.configure_device("Main_PSU", {"source_mode": "VOLT", "output_enabled": True})

# Start continuous asynchronous logging to SQLite
client.start_logging()
```

## License

This project is licensed under the zlib/libpng License - see the [LICENSE](LICENSE) file for details.

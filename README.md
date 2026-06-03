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

## Developer Guide

Welcome! This section covers everything you need to know to set up a local development environment, understand the underlying architecture, and contribute to `hermes-dm`.

### System Architecture Overview

`hermes-dm` uses a decoupled, event-driven, client-server architecture designed for high-performance, non-blocking laboratory hardware control.

* **The Hermes Client:** A lightweight, synchronous Python API exposed to user scripts or notebooks. It handles telemetry requests, sends command packets over ZeroMQ, and translates backend JSON error states back into native Python exceptions.
* **The Hermes Daemon:** A persistent, asynchronous background process (`asyncio`) handling incoming network traffic via ZeroMQ. 
* **Isolated Thread Pools:** To prevent slow hardware I/O (like instrument connection scans or legacy GPIB commands) from locking up the main asynchronous network event loop, the daemon uses dedicated OS thread pools (`asyncio.to_thread` and custom `ThreadPoolExecutor` instances) to isolate synchronous PyVISA drivers.

---

### Environment Setup

Follow these steps to set up an isolated development environment running your code in editable mode with all developer tools active.

1. **Clone the repository and navigate to the root directory:**
   ```bash
   git clone [https://github.com/cbeiraod/hermes-dm.git](https://github.com/cbeiraod/hermes-dm.git)
   cd hermes-dm
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the environment:**
   * **Linux / macOS:** `source .venv/bin/activate`
   * **Windows (Cmd):** `.venv\Scripts\activate.bat`
   * **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`

4. **Install the package in editable mode with development extras:**
   ```bash
   pip install -e ".[dev]"
   ```
   *Note: If you are using Zsh, make sure to wrap the target in quotes: `pip install -e ".[dev]"`*

5. **Install the local Git hooks:**
   ```bash
   pre-commit install
   ```

---

### Development Tools Stack

We use a modern, consolidated tool stack to enforce code quality, verify async test patterns, and automate package distribution. 

| Tool | Purpose | Standalone Command |
| :--- | :--- | :--- |
| **Pytest** | Test runner for client, server routing, and database logs | `pytest` |
| **Ruff** | Lightning-fast linter, formatter, and import sorter | `ruff check` (lint) <br> `ruff format` (style) |
| **Pre-commit** | Framework managing local Git hooks and code safety | `pre-commit run --all-files` |
| **Bump-my-version** | Automated single-source-of-truth version bumping | `bump-my-version bump [patch\|minor\|major]` |
| **Build** | Creates standard PEP 517 source archives and wheels | `python -m build` |
| **Twine** | Securely uploads distribution wheels to PyPI | `twine upload dist/*` |

#### Running Tools Standalone

* **Running the Test Suite:**
  To execute all test suites with verbose execution details:
  ```bash
  pytest -v
  ```

* **Running Linter/Formatter Manually:**
  While `pre-commit` intercepts formatting issues during git tracking, you can trigger individual sweeps manually:
  ```bash
  ruff check --fix     # Evaluates code quality rules and auto-fixes violations
  ruff format          # Enforces your project's code style rules across all files
  ```

* **Simulating a Pre-commit Run:**
  If you want to evaluate all files against the entire pre-commit stack (including trailing whitespace, end-of-file fixers, and forgotten debug statements) without committing code:
  ```bash
  pre-commit run --all-files
  ```

* **Executing a Release Version Bump:**
  To safely increment versions across your `pyproject.toml` and package `__init__.py` while auto-generating tracking commits and release candidate tags:
  ```bash
  bump-my-version bump minor
  ```

---

### CI/CD Infrastructure (GitHub Actions)

Automation pipelines are tracked inside `.github/workflows/`. They isolate compute footprints to keep automation efficient and free.

#### 1. Continuous Integration (`ci.yml`)
Triggers automatically on every push to `main`, pull request tracking, or creation of version tags (`v*.*.*`).
* **Fail-Fast Lint Gate:** Automatically triggers a clean cloud environment to test the full codebase against `pre-commit`. If formatting is irregular or a stray `breakpoint()` is exposed, the job drops immediately.
* **Linux Test Core:** Executes the complete async test matrix under an optimized caching system to evaluate package installs in seconds.
* **Extended Multi-OS Testing:** To control costs, tests targeting Windows and macOS runners are restricted. They execute **only** when a formal version release tag (e.g., `v0.2.0`) is discovered or when manually requested via the GitHub Actions UI.

#### 2. PyPI Package Deployment (Coming Soon)
* Triggers exclusively on published GitHub Releases.
* Automatically triggers the `build` pipeline, verifies package architecture integrity via `twine check`, and deploys clean production wheels securely onto the Python Package Index (PyPI).

## License

This project is licensed under the zlib/libpng License - see the [LICENSE](LICENSE) file for details.

Usage Guide
===========

Using Hermes-DM is a two-step process: starting the background daemon, and interacting with it via the client API.

1. Starting the Daemon
----------------------

The Daemon is a persistent background process that maintains connections to your physical instruments. It handles polling, database logging, and asynchronous hardware execution.

You can start the daemon from your terminal using the Typer CLI:

.. code-block:: bash

   hermes daemon start --port 5555 --db-dir ./data

Leave this terminal window open. The daemon is now listening for incoming ZeroMQ connections.

2. Using the Client
-------------------

In a new terminal window, Python script, or Jupyter Notebook, you can use the ``HermesClient`` to send commands and retrieve telemetry without blocking your local thread.

Here is a complete example of scanning the bus, connecting an instrument via auto-discovery, and interacting with it:

.. code-block:: python

   from hermes_dm.client.connection import HermesClient

   # Connect to the local daemon
   with HermesClient(host="localhost", port=5555) as client:

       # 1. Scan the local hardware bus for physical instruments
       resources = client.list_scpi_resources()
       print(f"Found resources: {resources}")

       # 2. Connect to an instrument using Auto-Discovery
       # Hermes will automatically determine the SCPI terminators and load the correct driver
       client.connect_device(
           name="Main_PSU",
           identifier="ASRL3::INSTR",
           model="auto"
       )

       # 3. Toggle Database Logging
       # Disable SQLite logging temporarily to prevent spamming the database during setup
       client.disable_db_logging("Main_PSU")

       # 4. Fetch live telemetry
       # This pulls the latest cached data from the daemon instantly, without waiting on hardware I/O
       # (Assuming a driver method exists to fetch voltage)
       data = client._send_command("get_telemetry", {"name": "Main_PSU"})
       print(f"Current Telemetry: {data}")

Command Line Utilities
----------------------

Hermes also provides convenient CLI commands for quick hardware interactions without writing Python scripts.

To scan for SCPI devices directly from the terminal:

.. code-block:: bash

   hermes device scan --host localhost --port 5555

import json
import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

import zmq


class HermesTelemetryListener:
    """
    Background listener for live telemetry data from the Hermes Daemon.
    Uses a ZeroMQ SUB socket and runs in a separate thread to avoid blocking.
    """

    def __init__(self, host: str = "localhost", port: int = 5556):
        self.host = host
        self.port = port

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{self.host}:{self.port}")

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def subscribe(self, topic_prefix: str = ""):
        """
        Subscribe to a specific topic to filter incoming data.
        Examples:
        - "" (Subscribes to ALL data)
        - "DATA.Main_PSU" (Only data from Main_PSU)
        - "DATA.Main_PSU.VOLTAGE" (Only voltage data from Main_PSU)
        """
        self.socket.setsockopt_string(zmq.SUBSCRIBE, topic_prefix)

    def unsubscribe(self, topic_prefix: str):
        """Remove a subscription."""
        self.socket.setsockopt_string(zmq.UNSUBSCRIBE, topic_prefix)

    def start(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Start listening in a background thread.
        The callback function will be triggered every time new data arrives.

        Callback signature must be: func(topic: str, data: dict)
        """
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Listener is already running.")

        self._stop_event.clear()

        # daemon=True ensures this thread dies automatically if your main script crashes/exits
        self._thread = threading.Thread(target=self._listen_loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background listener thread safely."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()

        self.socket.close()
        self.context.term()

    def _listen_loop(self, callback: Callable[[str, Dict[str, Any]], None]):
        """The internal loop running in the background thread."""

        # We use a Poller so we aren't permanently frozen waiting for recv_string()
        # This allows us to check self._stop_event every 500 milliseconds.
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)

        while not self._stop_event.is_set():
            socks = dict(poller.poll(500))

            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                try:
                    # Receive the raw string formatted as: "TOPIC {"json": "payload"}"
                    message = self.socket.recv_string()

                    # Split exactly once at the first space
                    topic, payload_str = message.split(" ", 1)
                    data = json.loads(payload_str)

                    # Trigger the user's function with the parsed data
                    callback(topic, data)

                except (ValueError, json.JSONDecodeError) as e:
                    print(f"Telemetry parse error: {e}")

    # Allow use as a context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

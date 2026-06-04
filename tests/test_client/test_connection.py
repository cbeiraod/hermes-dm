import json
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from hermes_dm.client.connection import HermesClient
from hermes_dm.client.connection import HermesError


@patch("zmq.Context")
def test_client_successful_command(mock_zmq_context):
    """Test that the client correctly formats and sends a JSON request."""

    # 1. Setup the mock socket
    mock_socket = MagicMock()
    mock_zmq_context.return_value.socket.return_value = mock_socket

    # 2. Define the fake JSON response from the Daemon
    mock_socket.recv_string.return_value = json.dumps({"status": "success", "message": "Logging started."})

    # 3. Execute the client code
    with HermesClient() as client:
        result = client.start_logging()

    # 4. Verify the client sent the exact JSON string we expect
    mock_socket.send_string.assert_called_once()
    sent_payload = json.loads(mock_socket.send_string.call_args[0][0])

    assert sent_payload["command"] == "start_logging"
    assert result == "Logging started."


@patch("zmq.Context")
def test_client_error_handling(mock_zmq_context):
    """Test that the client correctly translates daemon errors into Python exceptions."""

    mock_socket = MagicMock()
    mock_zmq_context.return_value.socket.return_value = mock_socket

    # Mock a failure state from the daemon
    mock_socket.recv_string.return_value = json.dumps({"status": "error", "message": "Voltage out of range."})

    with HermesClient() as client:
        # The client should detect 'error' and raise HermesError
        with pytest.raises(HermesError, match="Voltage out of range"):
            client.configure_device("Main_PSU", {"voltage_level": 9000})


@patch("zmq.Context")
def test_client_timeout(mock_zmq_context):
    """Test that the client doesn't freeze forever if the daemon crashes."""
    import zmq

    mock_socket = MagicMock()
    mock_zmq_context.return_value.socket.return_value = mock_socket

    # Force the socket to simulate a timeout exception
    mock_socket.recv_string.side_effect = zmq.error.Again()

    with HermesClient() as client:
        with pytest.raises(TimeoutError, match="No response from Hermes daemon"):
            client.list_devices()

import pytest

# Tell pytest that all tests in this file are async
pytestmark = pytest.mark.asyncio


async def test_auto_discovery_and_connect(simulated_daemon):
    """
    Tests that the system can scan the bus, query *IDN?, automatically map
    the response to the Keithley2410 driver, and successfully instantiate it.
    """
    daemon = simulated_daemon

    # 1. Verify the instrument is actually on the simulated bus
    scan_response = await daemon.handle_command("list_scpi_resources", {})
    assert scan_response["status"] == "success"

    # We expect the compiler to have loaded the full rack with the Keithley on GPIB 15
    assert "GPIB0::15::INSTR" in scan_response["data"]
    # Add a few other instruments here once they are implemented

    # 2. Trigger Auto-Discovery & Connection
    connect_args = {
        "identifier": "GPIB0::15::INSTR",
        "name": "Auto_Discovered_Keithley",
        "model": "auto",  # <-- This is the magic trigger we are testing!
    }

    connect_response = await daemon.handle_command("connect_device", connect_args)

    # 3. Assertions on the Connection State
    assert connect_response["status"] == "success"
    assert "Auto_Discovered_Keithley" in daemon.connected_devices

    # 4. The Ultimate Test: Did it pick the right class?
    # If discovery failed, it would either error out or pick a generic driver.
    # We want to mathematically prove it loaded the exact Keithley driver.
    active_instrument = daemon.connected_devices["Auto_Discovered_Keithley"]
    assert type(active_instrument).__name__ == "Keithley2410"
    assert daemon.connected_devices["Auto_Discovered_Keithley"].read_termination == '\n'
    assert daemon.connected_devices["Auto_Discovered_Keithley"].write_termination == '\n'

    # Verify the auto-discovery engine also correctly mapped the identifier
    assert active_instrument.identifier == "GPIB0::15::INSTR"

    # 5. Clean Teardown
    disconnect_response = await daemon.handle_command("disconnect_device", {"name": "Auto_Discovered_Keithley"})
    assert disconnect_response["status"] == "success"
    assert "Auto_Discovered_Keithley" not in daemon.connected_devices

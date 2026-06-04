import pytest


@pytest.mark.asyncio
async def test_daemon_list_resources(simulated_daemon):
    """Test that the daemon can successfully scan the hardware bus."""

    response = await simulated_daemon.handle_command("list_scpi_resources", {})

    expected_resources = simulated_daemon.visa_rm.list_resources()

    # 3. Verify
    assert response["status"] == "success"
    assert "GPIB0::15::INSTR" in response["data"]
    assert len(response["data"]) == len(expected_resources)


@pytest.mark.asyncio
@pytest.mark.parametrize("simulated_daemon", ["tests/simulators/racks/keithley2410_only_rack.yaml"], indirect=True)
async def test_daemon_list_resources_only_keithley2410(simulated_daemon):
    """Test that the daemon can successfully scan the hardware bus."""

    response = await simulated_daemon.handle_command("list_scpi_resources", {})

    # 3. Verify
    assert response["status"] == "success"
    assert "GPIB0::15::INSTR" in response["data"]
    assert len(response["data"]) == 2


@pytest.mark.asyncio
async def test_daemon_connect_device(simulated_daemon):
    """Test the hardware connection and driver instantiation flow."""

    args = {"name": "Test_PSU", "model": "Keithley2410", "identifier": "USB0::0x05E6::0x2410::1234567::0::INSTR"}

    response = await simulated_daemon.handle_command("connect_device", args)

    assert response["status"] == "success"
    assert "Test_PSU" in simulated_daemon.connected_devices

    # Verify the instrument was instantiated and connected successfully
    instrument = simulated_daemon.connected_devices["Test_PSU"]
    assert instrument.is_connected is True
    assert instrument.identifier == "USB0::0x05E6::0x2410::1234567::0::INSTR"


@pytest.mark.asyncio
async def test_daemon_db_logging_toggles(simulated_daemon):
    """Test the custom database logging toggles we added earlier."""

    # First, mock a connected device
    args = {"name": "Test_PSU", "model": "Keithley2410", "identifier": "ASRL2::INSTR"}
    await simulated_daemon.handle_command("connect_device", args)
    instrument = simulated_daemon.connected_devices["Test_PSU"]

    # By default, it should be True
    assert instrument.db_logging_enabled is True

    # Test disabling
    disable_args = {"name": "Test_PSU", "enable": False}
    await simulated_daemon.handle_command("set_db_logging", disable_args)
    assert instrument.db_logging_enabled is False

    # Test enabling
    enable_args = {"name": "Test_PSU", "enable": True}
    await simulated_daemon.handle_command("set_db_logging", enable_args)
    assert instrument.db_logging_enabled is True

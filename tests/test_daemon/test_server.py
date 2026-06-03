import pytest
from hermes_dm.daemon.server import PowerSupplyDaemon

@pytest.fixture
def daemon(temp_db, mock_visa_rm_keithley2410):
    """
    Creates an isolated daemon instance, injecting the temporary DB 
    and the mocked PyVISA Resource Manager.
    """
    d = PowerSupplyDaemon(db_directory=temp_db.db_directory)
    d.visa_rm = mock_visa_rm_keithley2410
    return d

@pytest.mark.asyncio
async def test_daemon_list_resources(daemon, mock_visa_rm_keithley2410):
    """Test that the daemon can successfully scan the hardware bus."""
    
    # 1. Tell the mock VISA manager what to pretend to find on the PC
    mock_visa_rm_keithley2410.list_resources.return_value = ("USB0::MOCK::INSTR", "ASRL3::INSTR")
    
    # 2. Call the router directly
    response = await daemon.handle_command("list_scpi_resources", {})
    
    # 3. Verify
    assert response["status"] == "success"
    assert "USB0::MOCK::INSTR" in response["data"]
    assert len(response["data"]) == 2

@pytest.mark.asyncio
async def test_daemon_connect_device(daemon, mock_visa_rm_keithley2410):
    """Test the hardware connection and driver instantiation flow."""
    
    args = {
        "name": "Test_PSU",
        "model": "Keithley2410",
        "identifier": "USB0::1234::INSTR"
    }
    
    response = await daemon.handle_command("connect_device", args)
    
    assert response["status"] == "success"
    assert "Test_PSU" in daemon.connected_devices
    
    # Verify the instrument was instantiated and connected successfully
    instrument = daemon.connected_devices["Test_PSU"]
    assert instrument.is_connected is True
    
    # Verify the underlying PyVISA mock was actually called by the Daemon
    mock_visa_rm_keithley2410.open_resource.assert_called_once_with("USB0::1234::INSTR")

@pytest.mark.asyncio
async def test_daemon_db_logging_toggles(daemon):
    """Test the custom database logging toggles we added earlier."""
    
    # First, mock a connected device
    args = {"name": "Test_PSU", "model": "Keithley2410", "identifier": "MOCK"}
    await daemon.handle_command("connect_device", args)
    instrument = daemon.connected_devices["Test_PSU"]
    
    # By default, it should be True
    assert instrument.db_logging_enabled is True
    
    # Test disabling
    disable_args = {"name": "Test_PSU", "enable": False}
    await daemon.handle_command("set_db_logging", disable_args)
    assert instrument.db_logging_enabled is False
    
    # Test enabling
    enable_args = {"name": "Test_PSU", "enable": True}
    await daemon.handle_command("set_db_logging", enable_args)
    assert instrument.db_logging_enabled is True
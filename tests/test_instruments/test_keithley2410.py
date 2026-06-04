import pytest

from hermes_dm.instruments.keithley2410 import Keithley2410


@pytest.mark.asyncio
async def test_keithley_lifecycle(mock_visa_rm_keithley2410):
    """Test connection, configuration, and reading of the Keithley driver."""

    # 1. Initialization (Inject the mock!)
    instrument = Keithley2410(name="Test_PSU", identifier="USB0::MOCK::INSTR", visa_rm=mock_visa_rm_keithley2410)

    # 2. Connection
    await instrument.connect()
    assert instrument.is_connected is True

    # Verify the underlying PyVISA mock was actually called
    mock_visa_rm_keithley2410.open_resource.assert_called_once_with("USB0::MOCK::INSTR")

    # 3. Configuration
    # Should fail if we pass a bad parameter
    with pytest.raises(ValueError):
        await instrument.configure({"source_mode": "MAGIC_MODE"})

    # Should succeed with valid parameters
    await instrument.configure({"source_mode": "VOLT", "output_enabled": True})
    assert instrument.config["output_enabled"] is True

    # 4. Reading Data
    readings = await instrument.read()

    # Based on our mock string "+1.20000E+01,+5.00000E-02...", it should parse:
    # 12.0 Volts and 0.05 Amps
    assert len(readings) == 2

    # Validate Voltage Output
    assert readings[0][0] == 1  # Channel
    assert readings[0][1] == "Voltage"  # Metric
    assert readings[0][2] == 12.0  # Value

    # Validate Current Output
    assert readings[1][1] == "Current"
    assert readings[1][2] == 0.05

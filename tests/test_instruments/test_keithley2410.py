import pytest

from hermes_dm.instruments.keithley2410 import Keithley2410


@pytest.mark.asyncio
@pytest.mark.parametrize("simulated_daemon", ["tests/simulators/racks/keithley2410_only_rack.yaml"], indirect=True)
async def test_keithley_lifecycle(simulated_daemon):
    """Test connection, configuration, and reading of the Keithley driver."""

    # 1. Initialization (Inject the simulated PyVISA manager and executor!)
    instrument = Keithley2410(
        name="Test_PSU",
        identifier="GPIB0::15::INSTR",
        visa_rm=simulated_daemon.visa_rm,
        gpib_executor=simulated_daemon.shared_gpib_executor,
    )

    # Mimic the daemon's auto-discovery injection!
    instrument.config["write_termination"] = "\n"
    instrument.config["read_termination"] = "\n"

    # 2. Connection
    await instrument.connect()

    # State verification: Ensure the boolean flipped and the underlying hardware resource exists
    assert instrument.is_connected is True
    assert instrument.instrument is not None

    # 3. Configuration
    # Should fail if we pass a bad parameter (Proves your Python validation works)
    with pytest.raises(ValueError):
        await instrument.configure({"source_mode": "MAGIC_MODE"})

    # Should succeed with valid parameters
    await instrument.configure({"source_mode": "VOLT", "output_enabled": True})
    assert instrument.config["output_enabled"] is True

    # 4. Reading Data
    # This now queries the YAML file, retrieves the string, and runs your real parsing logic!
    readings = await instrument.read()

    # Based on our YAML string "+1.20000E+01,+5.00000E-02...", it should parse:
    # 12.0 Volts and 0.05 Amps
    assert len(readings) == 2

    # Validate Voltage Output
    assert readings[0][0] == 1  # Channel
    assert readings[0][1] == "Voltage"  # Metric
    assert readings[0][2] == 12.0  # Value

    # Validate Current Output
    assert readings[1][1] == "Current"
    assert readings[1][2] == 0.05

    # 5. Cleanup
    await instrument.disconnect()

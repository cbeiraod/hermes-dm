import os
import tempfile

import pytest
import pytest_asyncio
import pyvisa
import yaml

from hermes_dm.daemon.db import DatabaseManager
from hermes_dm.daemon.server import PowerSupplyDaemon


def compile_sim_yaml(rack_filepath: str) -> str:
    """Reads a rack file, automatically pulls in required devices, and creates a compiled temp file."""

    # 1. Load the skeleton rack layout
    with open(rack_filepath, "r") as f:
        compiled_yaml = yaml.safe_load(f)

    compiled_yaml["devices"] = {}

    # 2. Look at the resources block to see which devices we need
    resources = compiled_yaml.get("resources", {})
    required_device_names = set(res["device"] for res in resources.values())

    # 3. Load the blueprint for each required device and stitch it in
    base_dir = os.path.dirname(os.path.dirname(rack_filepath))  # Go up to simulators/
    devices_dir = os.path.join(base_dir, "devices")

    for dev_name in required_device_names:
        dev_path = os.path.join(devices_dir, f"{dev_name}.yaml")
        with open(dev_path, "r") as f:
            compiled_yaml["devices"][dev_name] = yaml.safe_load(f)

    # 4. Write the final stitched YAML to a temporary file
    temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml")
    yaml.dump(compiled_yaml, temp_file)
    temp_file.close()

    # Return the path so pyvisa-sim can eat it
    return temp_file.name


@pytest.fixture
def temp_db():
    """
    Creates a temporary directory and an isolated DatabaseManager.
    Tears it down automatically after the test finishes.
    """
    # Setup phase
    with tempfile.TemporaryDirectory() as tmpdirname:
        db_manager = DatabaseManager(db_directory=tmpdirname)

        # Yield hands control over to the actual test
        yield db_manager

    # Teardown phase: The temporary directory is automatically deleted here


@pytest_asyncio.fixture
async def simulated_daemon(request, temp_db):
    # 1. Start with a default, but allow tests to override it via indirect=True
    default_rack = "tests/simulators/racks/full_rack.yaml"
    rack_path = getattr(request, "param", default_rack)

    # 2. COMPILE the modular YAMLs into a single temporary file!
    compiled_yaml_path = compile_sim_yaml(rack_path)

    # 3. Load the compiled temp file into pyvisa-sim
    sim_rm = pyvisa.ResourceManager(f"{compiled_yaml_path}@sim")

    # 4. Inject into daemon
    daemon = PowerSupplyDaemon(db_directory=temp_db.db_directory, cmd_port=0, pub_port=0)
    daemon.visa_rm = sim_rm

    yield daemon

    # 5. Teardown
    await daemon.stop()

    # Clean up the temporary compiled YAML file so we don't litter the OS
    if os.path.exists(compiled_yaml_path):
        os.remove(compiled_yaml_path)

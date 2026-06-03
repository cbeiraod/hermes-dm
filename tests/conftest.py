import pytest
import tempfile
import os
from hermes_dm.daemon.db import DatabaseManager

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

# tests/conftest.py
import pytest
import tempfile
import os
from unittest.mock import MagicMock
from hermes_dm.daemon.db import DatabaseManager

@pytest.fixture
def temp_db():
    """Creates a temporary isolated DatabaseManager."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        db_manager = DatabaseManager(db_directory=tmpdirname)
        yield db_manager 

@pytest.fixture
def mock_visa_rm_keithley2410():
    """
    Provides a mocked PyVISA ResourceManager.
    Intercepts SCPI queries and returns mock hardware data.
    """
    rm_mock = MagicMock()
    
    # Create the fake instrument that will be returned when connecting
    instrument_mock = MagicMock()
    
    # Define how the fake instrument responds to specific SCPI queries
    def mock_query(command: str) -> str:
        if command == ":READ?":
            # This is the exact string format a Keithley 2410 returns:
            # Voltage, Current, Resistance, Time, Status
            return "+1.20000E+01,+5.00000E-02,+2.40000E+02,+0.00000E+00,+0.00000E+00"
        
        if command == "*IDN?":
            return "KEITHLEY INSTRUMENTS INC.,MODEL 2410,1234567,C30"
            
        return ""
    
    # Attach our custom response function to the mock's query method
    instrument_mock.query.side_effect = mock_query
    
    # When the code calls rm.open_resource(), hand it our fake instrument
    rm_mock.open_resource.return_value = instrument_mock
    
    return rm_mock


import pyvisa
from pyvisa.constants import VI_READ_BUF_DISCARD, VI_WRITE_BUF_DISCARD
from typing import Tuple, Optional

def auto_discover_instrument(
    rm: pyvisa.ResourceManager, 
    identifier: str
) -> Tuple[str, str, str]:
    """
    Attempts to identify an unknown instrument via *IDN? using a double-loop 
    terminator sweep. 
    
    Returns: (IDN_String, Write_Terminator, Read_Terminator)
    Raises: ConnectionError if device cannot be identified.
    """
    try:
        instrument = rm.open_resource(identifier)
    except pyvisa.VisaIOError as e:
        raise ConnectionError(f"Could not open port {identifier}: {e}")

    # Standard terminators to try (ordered by statistical likelihood)
    terminators = ['\n', '\r\n', '\r', '']
    
    original_timeout = instrument.timeout
    instrument.timeout = 500  # 500ms timeout for fast failure sweeps
    
    idn_response: Optional[str] = None
    found_write_term: Optional[str] = None
    found_read_term: Optional[str] = None

    try:
        for w_term in terminators:
            for r_term in terminators:
                try:
                    instrument.write_termination = w_term
                    instrument.read_termination = r_term
                    
                    # 1. Send IDN query
                    response = instrument.query("*IDN?")
                    
                    # 2. If we get here, it worked! Save the parameters.
                    idn_response = response.strip()
                    found_write_term = w_term
                    found_read_term = r_term
                    break
                    
                except pyvisa.VisaIOError:
                    # Scrub hardware buffers
                    try: instrument.clear()
                    except pyvisa.VisaIOError: pass
                    
                    # Scrub local PC buffers
                    try: instrument.flush(VI_READ_BUF_DISCARD | VI_WRITE_BUF_DISCARD)
                    except pyvisa.VisaIOError: pass
            
            if idn_response:
                break # Break outer loop if we found it

    finally:
        # Restore timeout and gracefully close the temporary discovery session
        try:
            instrument.timeout = original_timeout
            instrument.close()
        except:
            pass

    if not idn_response:
        raise ConnectionError(f"Failed to communicate with {identifier} using any terminator combination.")
        
    return idn_response, found_write_term, found_read_term
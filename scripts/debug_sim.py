import logging

import pyvisa

# 1. Turn on the debug logger. This will force pyvisa-sim to
# print exactly what it is thinking when it reads your YAML file.
logging.basicConfig(level=logging.DEBUG)

print("--- Initializing Simulator ---")
# 2. Make sure this path exactly matches where your file is!
try:
    rm = pyvisa.ResourceManager("tests/simulators/test.yaml@sim")
except Exception as e:
    print(f"CRASH DURING INIT: {e}")
    exit(1)

print("\n--- Listing Resources ---")
try:
    resources = rm.list_resources()
    print(f"SUCCESS! Found: {resources}")
except Exception as e:
    print(f"FAILED TO LIST RESOURCES: {e}")

Installation
============

Prerequisites
-------------

Hermes-DM relies on PyVISA to communicate with physical hardware. You must have a working VISA backend installed on your system.

* **Windows/macOS:** We recommend installing `NI-VISA <https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html>`_, but ``pyvisa-py`` will work as well.
* **Linux:** You can use the pure-Python backend by installing ``pyvisa-py`` alongside this package.

Standard Installation (End Users)
---------------------------------

*(Note: Hermes-DM is currently in pre-release. Once published to PyPI, you can install it via pip.)*

To install the latest stable release:

.. code-block:: bash

   python -m pip install hermes-dm

To install with the pure-Python VISA backend (recommended for Linux):

.. code-block:: bash

   python -m pip install hermes-dm[pyvisa-py]

Developer Installation
----------------------

If you want to contribute to the project or run the test suite, install the package from source in "editable" mode.

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/cbeiraod/hermes-dm.git
      cd hermes-dm

2. Create and activate a virtual environment:

   .. code-block:: bash

      python -m venv .venv
      source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

3. Install with development and documentation tools:

   .. code-block:: bash

      pip install -e ".[dev,docs]"

4. Install the pre-commit Git hooks:

   .. code-block:: bash

      pre-commit install

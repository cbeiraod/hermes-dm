import os
import sys

# Tell Sphinx where to find the hermes_dm source code for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
project = "Hermes-DM"
copyright = "2026, Cristóvão Beirão da Cruz e Silva"
author = "Cristóvão Beirão da Cruz e Silva"

# The full version, including alpha/beta/rc tags
release = "0.0.1"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",        # Core library for extracting docstrings
    "sphinx.ext.napoleon",       # Support for Google/NumPy-style docstrings
    "sphinx.ext.viewcode",       # Adds a "[source]" link to read the underlying code
    "sphinx_autodoc_typehints",  # Merges type hints directly into the parameter descriptions
]

# Do not sort alphabetically; keep the order of methods as defined in the source code
autodoc_member_order = 'bysource'

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# We use Furo, the modern standard for Python docs
html_theme = "furo"
html_static_path = ["_static"]
html_title = "Hermes-DM Documentation"

# Optional: Add a logo if you have one
# html_logo = "_static/logo.png"
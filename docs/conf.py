# Configuration file for the Sphinx documentation builder.

import os
import sys

project = 'zuspec-fe-pss'
copyright = '2026, Matthew Ballance'
author = 'Matthew Ballance'

project_dir = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(project_dir, "src"))

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'alabaster'
html_static_path = []

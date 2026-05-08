"""Sphinx configuration for IS Matrix Forge documentation."""

from __future__ import annotations

project = "IS Matrix Forge"
author = "Inspyre Softworks"
copyright = "2026, Inspyre Softworks"

extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

master_doc = "index"

html_theme = "alabaster"

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

html_title = "IS Matrix Forge"
html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_theme_options = {
    "sidebar_hide_name": False,
    "top_of_page_button": "edit",
    "source_repository": "https://github.com/Inspyre-Softworks/IS-Matrix-Forge",
    "source_branch": "master",
    "source_directory": "/",
    "light_css_variables": {
        "color-brand-primary": "#5b4ae8",
        "color-brand-content": "#3d2f9a",
        "color-background-primary": "#f7f6ff",
        "color-background-secondary": "#efebff",
        "color-admonition-background": "#eef3ff",
        "color-highlight-on-target": "#eae4ff",
        "color-inline-code-background": "#e6e1ff",
        "color-foreground-primary": "#1e1a33",
        "color-foreground-secondary": "#4d4b63",
    },
    "dark_css_variables": {
        "color-brand-primary": "#bba7ff",
        "color-brand-content": "#d8cbff",
        "color-background-primary": "#120f1c",
        "color-background-secondary": "#1b1630",
        "color-admonition-background": "#1d1b2c",
        "color-highlight-on-target": "#2a2341",
        "color-inline-code-background": "#201b2e",
        "color-foreground-primary": "#f3f1ff",
        "color-foreground-secondary": "#c7c2dc",
    },
}

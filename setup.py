#!/usr/bin/env python3

"""
Minimal setup.py for compatibility with older tools.
Modern packaging configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages

# Find packages but exclude test directories
packages = find_packages(exclude=[
    "tests*", 
    "test*", 
    "testing*",
    "*.tests*",
    "*.test*",
    "*.testing*"
])

setup(
    packages=packages,
    # All other configuration is now in pyproject.toml
)
"""
cargo-orchestrator: A Python library for running cargo build and parsing its output.

This library provides a simple interface to run cargo build commands with various
options and parse the resulting errors and warnings.
"""

from .builder import CargoBuilder, BuildResult, BuildMessage
from .parser import CargoOutputParser

__version__ = "0.1.0"
__all__ = ["CargoBuilder", "BuildResult", "BuildMessage", "CargoOutputParser"]
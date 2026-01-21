"""
Local fixtures for condition_parser tests
"""
import sys
from pathlib import Path

import pytest

from tests.conftest import logger, module_logger  # noqa: F401

# Add parent plugin directory to sys.path
_plugin_dir = Path(__file__).parent.parent.parent  # plugins/utilities/core/
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Import through subfolder, preserving package structure for relative imports
from condition_parser.condition_parser import ConditionParser


@pytest.fixture(scope="session")
def parser(module_logger):
    """Creates ConditionParser once per test session (maximum optimization)"""
    return ConditionParser(logger=module_logger)

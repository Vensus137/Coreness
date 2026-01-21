"""
Local fixtures for placeholder_processor tests
"""
import sys
from pathlib import Path

import pytest

# Imports from other plugins (foundation) remain absolute
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager

# Import fixtures from root tests/conftest via absolute path
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
    
from tests.conftest import logger, module_logger  # noqa: F401

# Add parent plugin directory to sys.path
# Import PlaceholderProcessor via full module name preserving package structure
_plugin_dir = Path(__file__).parent.parent.parent  # plugins/utilities/core/
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Import through subfolder, preserving package structure for relative imports
from placeholder_processor.placeholder_processor import PlaceholderProcessor


@pytest.fixture(scope="session")
def _plugins_manager(module_logger):
    """Creates PluginsManager once per test session (maximum optimization)"""
    return PluginsManager(logger=module_logger.get_logger("plugins_manager"))


@pytest.fixture(scope="session")
def _settings_manager(_plugins_manager, module_logger):
    """Creates SettingsManager once per test session (maximum optimization)"""
    return SettingsManager(logger=module_logger.get_logger("settings_manager"), plugins_manager=_plugins_manager)


@pytest.fixture(scope="session")
def processor(module_logger, _settings_manager):
    """Creates PlaceholderProcessor once per test session (maximum optimization)"""
    return PlaceholderProcessor(logger=module_logger, settings_manager=_settings_manager)


def assert_equal(actual, expected, message=""):
    """Simplified equality check with type normalization for string results"""
    # If actual is string and expected is number or bool, normalize
    if isinstance(actual, str):
        if isinstance(expected, bool):
            # Convert string "True"/"False" to bool
            if actual == "True":
                actual = True
            elif actual == "False":
                actual = False
        elif isinstance(expected, (int, float)):
            # Convert string to number
            try:
                actual = float(actual) if isinstance(expected, float) else int(actual)
            except (ValueError, TypeError):
                pass
    
    assert actual == expected, f"{message}: expected {expected!r}, got {actual!r}"


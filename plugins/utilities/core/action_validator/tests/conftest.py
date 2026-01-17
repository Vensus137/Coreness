"""
Локальные фикстуры для тестов action_validator
"""
import sys
from pathlib import Path

import pytest

from tests.conftest import logger, module_logger  # noqa: F401

# Автоматически добавляем родительскую директорию плагина в sys.path
# Это позволяет использовать импорты вида "from action_validator import ..."
# вместо "from plugins.utilities.core.action_validator.action_validator import ..."
# и делает тесты независимыми от структуры папок выше уровня плагина
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from action_validator import ActionValidator


class MockSettingsManager:
    """Мок SettingsManager для тестов"""
    
    def __init__(self):
        # Тестовые схемы действий
        self._plugin_info = {
            'test_service': {
                'actions': {
                    'simple_action': {
                        'input': {
                            'data': {
                                'properties': {
                                    'name': {
                                        'type': 'string',
                                        'optional': False
                                    },
                                    'age': {
                                        'type': 'integer',
                                        'optional': True
                                    }
                                }
                            }
                        }
                    },
                    'action_with_constraints': {
                        'input': {
                            'data': {
                                'properties': {
                                    'prompt': {
                                        'type': 'string',
                                        'optional': False,
                                        'min_length': 1,
                                        'max_length': 100
                                    },
                                    'temperature': {
                                        'type': 'float',
                                        'optional': True,
                                        'min': 0.0,
                                        'max': 2.0
                                    },
                                    'json_mode': {
                                        'type': 'string',
                                        'optional': True,
                                        'enum': ['json_object', 'json_schema']
                                    }
                                }
                            }
                        }
                    },
                    'action_with_optional_constraints': {
                        'input': {
                            'data': {
                                'properties': {
                                    'required_field': {
                                        'type': 'string',
                                        'optional': False,
                                        'min_length': 1
                                    },
                                    'optional_string_min_length': {
                                        'type': 'string',
                                        'optional': True,
                                        'min_length': 1,
                                        'max_length': 100
                                    },
                                    'optional_string_pattern': {
                                        'type': 'string',
                                        'optional': True,
                                        'pattern': '^[A-Z]+$'
                                    },
                                    'optional_number_min_max': {
                                        'type': 'integer',
                                        'optional': True,
                                        'min': 1,
                                        'max': 100
                                    },
                                    'optional_float_min_max': {
                                        'type': 'float',
                                        'optional': True,
                                        'min': 0.0,
                                        'max': 1.0
                                    }
                                }
                            }
                        }
                    },
                    'action_with_union': {
                        'input': {
                            'data': {
                                'properties': {
                                    'target_chat_id': {
                                        'type': 'integer|array',
                                        'optional': True
                                    },
                                    'state': {
                                        'type': 'string|None',
                                        'optional': False
                                    }
                                }
                            }
                        }
                    },
                    'action_with_nested_array': {
                        'input': {
                            'data': {
                                'properties': {
                                    'items': {
                                        'type': 'array',
                                        'optional': False,
                                        'items': {
                                            'properties': {
                                                'id': {
                                                    'type': 'integer',
                                                    'optional': False
                                                },
                                                'name': {
                                                    'type': 'string',
                                                    'optional': True
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    'action_no_schema': {
                        'input': {}
                    },
                    'action_with_optional_array': {
                        'input': {
                            'data': {
                                'properties': {
                                    'required_field': {
                                        'type': 'string',
                                        'optional': False
                                    },
                                    'optional_array': {
                                        'type': 'array',
                                        'optional': True
                                    },
                                    'optional_integer': {
                                        'type': 'integer',
                                        'optional': True
                                    },
                                    'optional_string': {
                                        'type': 'string',
                                        'optional': True
                                    },
                                    'optional_union_array': {
                                        'type': 'integer|array',
                                        'optional': True
                                    },
                                    'optional_union_string': {
                                        'type': 'string|array',
                                        'optional': True
                                    }
                                }
                            }
                        }
                    },
                    'action_with_from_config': {
                        'input': {
                            'data': {
                                'properties': {
                                    'prompt': {
                                        'type': 'string',
                                        'optional': False
                                    },
                                    'openrouter_token': {
                                        'type': 'string',
                                        'optional': False,
                                        'from_config': True
                                    }
                                }
                            }
                        }
                    },
                    'action_with_optional_from_config': {
                        'input': {
                            'data': {
                                'properties': {
                                    'prompt': {
                                        'type': 'string',
                                        'optional': False
                                    },
                                    'openrouter_token': {
                                        'type': 'string',
                                        'optional': False,
                                        'from_config': True
                                    },
                                    'optional_token': {
                                        'type': 'string',
                                        'optional': True,
                                        'from_config': True
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def get_plugin_info(self, plugin_name: str):
        """Получение информации о плагине"""
        return self._plugin_info.get(plugin_name)
    
    def get_plugin_settings(self, plugin_name: str):
        """Получение настроек плагина"""
        return {}


@pytest.fixture(scope="session")
def mock_settings_manager():
    """Создает MockSettingsManager один раз на всю сессию тестов (максимальная оптимизация)"""
    return MockSettingsManager()


@pytest.fixture(scope="session")
def validator(module_logger, mock_settings_manager):
    """Создает ActionValidator один раз на всю сессию тестов (максимальная оптимизация)"""
    return ActionValidator(logger=module_logger, settings_manager=mock_settings_manager)


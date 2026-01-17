"""
Unit-тесты для модуля user_input
"""
from unittest.mock import patch

import pytest
from modules.utils.user_input import confirm, confirm_required


@pytest.mark.unit
class TestUserInput:
    """Тесты для функций обработки пользовательского ввода"""
    
    def test_confirm_with_default_false_accepts_y(self):
        """Проверяет что confirm с default=False принимает 'y'"""
        with patch("builtins.input", return_value="y"):
            result = confirm("Продолжить?", default=False)
            assert result is True
    
    def test_confirm_with_default_false_accepts_yes(self):
        """Проверяет что confirm с default=False принимает 'yes'"""
        with patch("builtins.input", return_value="yes"):
            result = confirm("Продолжить?", default=False)
            assert result is True
    
    def test_confirm_with_default_false_rejects_n(self):
        """Проверяет что confirm с default=False отклоняет 'n'"""
        with patch("builtins.input", return_value="n"):
            result = confirm("Продолжить?", default=False)
            assert result is False
    
    def test_confirm_with_default_false_uses_default_on_empty(self):
        """Проверяет что confirm с default=False использует дефолт при пустом вводе"""
        with patch("builtins.input", return_value=""):
            result = confirm("Продолжить?", default=False)
            assert result is False
    
    def test_confirm_with_default_true_uses_default_on_empty(self):
        """Проверяет что confirm с default=True использует дефолт при пустом вводе"""
        with patch("builtins.input", return_value=""):
            result = confirm("Продолжить?", default=True)
            assert result is True
    
    def test_confirm_with_default_true_accepts_n(self):
        """Проверяет что confirm с default=True принимает 'n'"""
        with patch("builtins.input", return_value="n"):
            result = confirm("Продолжить?", default=True)
            assert result is False
    
    def test_confirm_retries_on_invalid_input(self):
        """Проверяет что confirm повторяет запрос при неверном вводе"""
        with patch("builtins.input", side_effect=["invalid", "y"]):
            result = confirm("Продолжить?", default=False)
            assert result is True
    
    def test_confirm_accepts_russian_yes(self):
        """Проверяет что confirm принимает русские варианты 'да'"""
        with patch("builtins.input", return_value="да"):
            result = confirm("Продолжить?", default=False)
            assert result is True
    
    def test_confirm_accepts_russian_no(self):
        """Проверяет что confirm принимает русские варианты 'нет'"""
        with patch("builtins.input", return_value="нет"):
            result = confirm("Продолжить?", default=False)
            assert result is False
    
    def test_confirm_required_accepts_yes(self):
        """Проверяет что confirm_required принимает 'yes'"""
        with patch("builtins.input", return_value="yes"):
            result = confirm_required("Продолжить?")
            assert result is True
    
    def test_confirm_required_accepts_y(self):
        """Проверяет что confirm_required принимает 'y'"""
        with patch("builtins.input", return_value="y"):
            result = confirm_required("Продолжить?")
            assert result is True
    
    def test_confirm_required_rejects_no(self):
        """Проверяет что confirm_required отклоняет 'no'"""
        with patch("builtins.input", return_value="no"):
            result = confirm_required("Продолжить?")
            assert result is False
    
    def test_confirm_required_retries_on_invalid_input(self):
        """Проверяет что confirm_required повторяет запрос при неверном вводе"""
        with patch("builtins.input", side_effect=["invalid", "yes"]):
            result = confirm_required("Продолжить?")
            assert result is True
    
    def test_confirm_required_retries_on_empty_input(self):
        """Проверяет что confirm_required повторяет запрос при пустом вводе"""
        with patch("builtins.input", side_effect=["", "yes"]):
            result = confirm_required("Продолжить?")
            assert result is True


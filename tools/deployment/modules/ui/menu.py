"""
Модуль для работы с меню
"""

from typing import Callable, List, Optional

from modules.ui.output import Colors, get_formatter


class MenuItem:
    """Элемент меню"""
    
    def __init__(self, key: str, label: str, handler: Callable, description: Optional[str] = None):
        self.key = key
        self.label = label
        self.handler = handler
        self.description = description


class Menu:
    """Класс для работы с меню"""
    
    def __init__(self, title: str, items: List[MenuItem]):
        self.title = title
        self.items = items
        self.formatter = get_formatter()
    
    def show(self):
        """Показывает меню"""
        self.formatter.print_header(self.title)
        
        for item in self.items:
            if item.description:
                # Описание на той же строке, приглушенным цветом
                description_text = self.formatter._colorize(f" — {item.description}", Colors.DIM)
                print(f"{item.key}. {item.label}{description_text}")
            else:
                print(f"{item.key}. {item.label}")
        
        self.formatter.print_separator()
    
    def get_choice(self) -> Optional[str]:
        """Получает выбор пользователя"""
        choice = input("\nВыберите действие: ").strip()
        return choice
    
    def handle_choice(self, choice: str) -> bool:
        """Обрабатывает выбор пользователя. Возвращает True если нужно продолжить"""
        if choice == "0":
            return False
        
        for item in self.items:
            if item.key == choice:
                try:
                    item.handler()
                    return True
                except KeyboardInterrupt:
                    print("\n\n⚠️ Операция прервана пользователем")
                    return True
                except Exception as e:
                    self.formatter.print_error(f"Ошибка выполнения: {e}")
                    return True
        
        self.formatter.print_error("Неверный выбор. Попробуйте снова.")
        return True
    
    def run(self):
        """Запускает интерактивное меню"""
        try:
            while True:
                self.show()
                choice = self.get_choice()
                
                if not self.handle_choice(choice):
                    self.formatter.print_info("До свидания!")
                    break
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Работа прервана пользователем")


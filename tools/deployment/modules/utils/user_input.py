"""
Утилита для обработки пользовательского ввода
Унифицированные функции для подтверждений и выбора
"""


def confirm(prompt: str, default: bool = False) -> bool:
    """
    Запрашивает подтверждение у пользователя
    
    Примеры:
        confirm("Продолжить обновление?", default=False)  # (y/N)
        confirm("Удалить файлы?", default=True)  # (Y/n)
    """
    if default:
        choice_text = "(Y/n)"
    else:
        choice_text = "(y/N)"
    
    while True:
        user_input = input(f"{prompt} {choice_text}: ").strip().lower()
        
        # Если пустой ввод - используем дефолт
        if not user_input:
            return default
        
        # Принимаем различные варианты подтверждения
        if user_input in ['y', 'yes', 'да', 'д']:
            return True
        elif user_input in ['n', 'no', 'нет', 'н']:
            return False
        else:
            default_hint = "Y" if default else "N"
            print(f"❌ Пожалуйста, введите 'y' или 'n' (или нажмите Enter для {default_hint})")

def confirm_required(prompt: str) -> bool:
    """
    Запрашивает обязательное подтверждение (без дефолта)
    
    Примеры:
        confirm_required("Это действие необратимо! Продолжить?")  # (y/n)
    """
    while True:
        user_input = input(f"{prompt} (y/n): ").strip().lower()
        
        if user_input in ['yes', 'y', 'да', 'д']:
            return True
        elif user_input in ['no', 'n', 'нет', 'н']:
            return False
        else:
            print("❌ Используйте 'y' или 'n'")


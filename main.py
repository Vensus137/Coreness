from dotenv import load_dotenv

from app.application import Application

# Загружаем переменные окружения
load_dotenv()

if __name__ == "__main__":
    # Создаем и запускаем приложение
    app = Application()
    app.run_sync()
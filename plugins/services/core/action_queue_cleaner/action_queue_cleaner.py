import asyncio
from datetime import timedelta


class ActionQueueCleaner:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_service = kwargs['database_service']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings('action_queue_cleaner')
        self.queue_read_interval = settings.get('queue_read_interval', 600)  # секунд
        self.queue_batch_size = settings.get('queue_batch_size', 1000)
        self.older_than_hours = settings.get('older_than_hours', 2)
        self.threshold_for_vacuum = settings.get('threshold_for_vacuum', 10000)

    async def run(self):
        self.logger.info(f"старт фонового цикла (interval={self.queue_read_interval}s, batch_size={self.queue_batch_size}, older_than={self.older_than_hours}h)")
        while True:
            try:
                deleted_total = 0
                while True:
                    deleted = self._delete_batch()
                    deleted_total += deleted
                    if deleted < self.queue_batch_size:
                        break
                    await asyncio.sleep(1)  # пауза между батчами
        
                if deleted_total >= self.threshold_for_vacuum:
                    self._vacuum()
            except Exception as e:
                self.logger.error(f"ActionQueueCleaner: ошибка при чистке: {e}")
            await asyncio.sleep(self.queue_read_interval)

    def _delete_batch(self) -> int:
        with self.database_service.session_scope('actions') as (session, repos):
            actions_repo = repos['actions']
            # Удаляем старые записи по времени
            cutoff = self.datetime_formatter.now_local() - timedelta(hours=self.older_than_hours)
            deleted = actions_repo.cleanup_old_actions(cutoff, batch_size=self.queue_batch_size)
            session.commit()
            return deleted

    def _vacuum(self):

        try:
            self.database_service.engine.execute("VACUUM;")
    
        except Exception as e:
            self.logger.error(f"ActionQueueCleaner: ошибка VACUUM: {e}")

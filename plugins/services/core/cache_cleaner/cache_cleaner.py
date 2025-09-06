import asyncio
import os
from datetime import timedelta
from typing import Tuple


class CacheCleaner:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_service = kwargs['database_service']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.settings_manager = kwargs['settings_manager']

        settings = self.settings_manager.get_plugin_settings('cache_cleaner')
        self.queue_read_interval: int = settings.get('queue_read_interval', 600)
        self.queue_batch_size: int = settings.get('queue_batch_size', 1000)
        self.older_than_with_file_hours: int = settings.get('older_than_with_file_hours', 240)
        self.older_than_without_file_hours: int = settings.get('older_than_without_file_hours', 2400)
        self.threshold_for_vacuum: int = settings.get('threshold_for_vacuum', 10000)
        self.dry_run: bool = settings.get('dry_run', False)

    async def run(self):
        self.logger.info(
            f"старт фонового цикла cache_cleaner (interval={self.queue_read_interval}s, batch_size={self.queue_batch_size}, "
            f"with_file_retention={self.older_than_with_file_hours}h, without_file_retention={self.older_than_without_file_hours}h)"
        )
        while True:
            try:
                deleted_total = 0

                # Сначала удаляем записи с файлами
                while True:
                    deleted = self._delete_batch(with_files=True)
                    deleted_total += deleted
                    if deleted < self.queue_batch_size:
                        break
                    await asyncio.sleep(1)

                # Затем записи без файлов
                while True:
                    deleted = self._delete_batch(with_files=False)
                    deleted_total += deleted
                    if deleted < self.queue_batch_size:
                        break
                    await asyncio.sleep(1)

                if deleted_total >= self.threshold_for_vacuum and not self.dry_run:
                    self._vacuum()
            except Exception as e:
                self.logger.error(f"CacheCleaner: ошибка при чистке: {e}")
            await asyncio.sleep(self.queue_read_interval)

    def _get_cutoffs(self) -> Tuple[object, object]:
        now = self.datetime_formatter.now_local()
        with_file_cutoff = now - timedelta(hours=self.older_than_with_file_hours)
        without_file_cutoff = now - timedelta(hours=self.older_than_without_file_hours)
        return with_file_cutoff, without_file_cutoff

    def _delete_batch(self, with_files: bool) -> int:
        with_file_cutoff, without_file_cutoff = self._get_cutoffs()
        cutoff = with_file_cutoff if with_files else without_file_cutoff

        deleted_count = 0
        with self.database_service.session_scope('cache') as (session, repos):
            cache_repo = repos['cache']

            records = cache_repo.list_old_cache(cutoff=cutoff, with_files=with_files, limit=self.queue_batch_size)
            if not records:
                return 0

            for rec in records:
                hash_key = rec.get('hash_key')
                file_path = rec.get('hash_file_path')
                if self.dry_run:
                    self.logger.info(f"[dry-run] удаление кэша hash_key={hash_key} file_path={file_path or '-'}")
                    deleted_count += 1
                    continue

                # Пытаемся удалить связанный файл здесь (с резолвингом относительного пути)
                if with_files and file_path:
                    try:
                        resolved_path = file_path
                        if not os.path.isabs(file_path):
                            try:
                                resolved_path = self.settings_manager.resolve_file_path(file_path)
                            except Exception:
                                resolved_path = file_path

                        if os.path.exists(resolved_path):
                            os.remove(resolved_path)
                        else:
                            pass
                    except Exception as fe:
                        self.logger.error(f"Ошибка удаления файла {file_path}: {fe}")

                try:
                    ok = cache_repo.delete_cache(hash_key)
                    if ok:
                        deleted_count += 1
                except Exception as e:
                    self.logger.error(f"CacheCleaner: ошибка удаления {hash_key}: {e}")

        return deleted_count

    def _vacuum(self):
        try:
            self.database_service.engine.execute("VACUUM;")
        except Exception as e:
            self.logger.error(f"CacheCleaner: ошибка VACUUM: {e}")



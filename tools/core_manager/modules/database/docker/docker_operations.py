"""Docker operations for PostgreSQL backup/restore."""

import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .compose_finder import get_compose_cwd, get_compose_file_list


def _is_container_running(container_id: str) -> bool:
    """Check if a Docker container is running by id or name."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    except Exception:
        return False


def _extract_container_id_from_error(stderr: str) -> Optional[str]:
    """Extract container ID from 'already in use' error message."""
    # "already in use by container \"c3c81402a582...\""
    match = re.search(r'by container\s+"([a-f0-9]+)"', stderr)
    return match.group(1) if match else None


class DockerPostgresOperations:
    """PostgreSQL operations through Docker Compose."""
    
    def __init__(self, project_root: Path, docker_compose_config: dict, translator):
        self.project_root = project_root
        self.docker_compose_config = docker_compose_config
        self.translator = translator
    
    def _compose_f_args(self, compose_files: list) -> list:
        """Build -f file1 -f file2 list for docker compose."""
        return [arg for f in compose_files for arg in ("-f", str(f))]

    def _start_service(self, compose_files: list, cwd: Path, service_name: str, formatter) -> Tuple[bool, Optional[str]]:
        """Start Docker service if not running. Returns (success, container_id). When 'already in use' and running, returns (True, container_id) to use with docker exec."""
        try:
            formatter.print_info(self.translator.get("database.docker_starting_service", service=service_name))
            f_args = self._compose_f_args(compose_files)

            result = subprocess.run(
                ["docker", "compose"] + f_args + ["up", "-d", service_name],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else ""
                # Container already exists and may be running - use its id for docker exec
                if "already in use" in error_msg.lower():
                    container_id = _extract_container_id_from_error(result.stderr or "")
                    if container_id and _is_container_running(container_id):
                        formatter.print_success(f"✓ {self.translator.get('database.docker_service_already_running')}")
                        return True, container_id
                formatter.print_error(
                    self.translator.get("database.docker_service_start_failed", error=error_msg or "Unknown error")
                )
                return False, None

            # Wait for service to be ready (max 10 seconds)
            for _ in range(10):
                time.sleep(1)
                check_result = subprocess.run(
                    ["docker", "compose"] + f_args + ["ps", "--status", "running", "-q", service_name],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if check_result.returncode == 0 and check_result.stdout.strip():
                    formatter.print_success(f"✓ {self.translator.get('database.docker_service_started')}")
                    return True, None

            formatter.print_error(self.translator.get("database.docker_service_start_failed", error="Service did not start in time"))
            return False, None

        except Exception as e:
            formatter.print_error(self.translator.get("database.docker_service_start_failed", error=str(e)))
            return False, None
    
    def backup(self, service_name: str, environment: str, database: str, username: str, backup_file: Path, formatter) -> bool:
        """Create backup using pg_dump in Docker container."""
        compose_files = get_compose_file_list(self.project_root, environment, self.docker_compose_config)
        if not compose_files:
            formatter.print_error(self.translator.get("database.docker_compose_not_found"))
            return False
        cwd = get_compose_cwd(compose_files[0], self.docker_compose_config)
        f_args = self._compose_f_args(compose_files)

        try:
            # Check if service is running, if not - try to start it
            container_id = None
            check_cmd = ["docker", "compose"] + f_args + ["ps", "--status", "running", "-q", service_name]
            check_result = subprocess.run(
                check_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_result.returncode != 0 or not check_result.stdout.strip():
                # Service not running, try to start it (may return container_id when "already in use")
                ok, container_id = self._start_service(compose_files, cwd, service_name, formatter)
                if not ok:
                    formatter.print_error(self.translator.get("database.docker_service_start_hint"))
                    return False

            # Create temp file inside container for dump
            container_dump = f"/tmp/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"

            # Execute pg_dump with compression: use docker exec when we have container_id (compose doesn't see it)
            # Use -h 127.0.0.1 to force IPv4 TCP connection (IPv6 ::1 may not be allowed in pg_hba.conf)
            # -Z 9 enables maximum compression level
            if container_id:
                cmd = ["docker", "exec", container_id, "pg_dump", "-h", "127.0.0.1", "-U", username, "-d", database, "-F", "c", "-Z", "9", "-f", container_dump]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            else:
                cmd = [
                    "docker", "compose"] + f_args + [
                    "exec", "-T", service_name,
                    "pg_dump", "-h", "127.0.0.1", "-U", username, "-d", database, "-F", "c", "-Z", "9", "-f", container_dump,
                ]
                result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                if result.stderr:
                    formatter.print_error(
                        self.translator.get("database.docker_pg_dump_failed", error=result.stderr.strip())
                    )
                return False

            # Copy dump file from container to host
            if container_id:
                copy_cmd = ["docker", "cp", f"{container_id}:{container_dump}", str(backup_file)]
                copy_result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)
            else:
                copy_cmd = ["docker", "compose"] + f_args + ["cp", f"{service_name}:{container_dump}", str(backup_file)]
                copy_result = subprocess.run(copy_cmd, cwd=cwd, capture_output=True, text=True, timeout=60)

            if copy_result.returncode != 0:
                if copy_result.stderr:
                    formatter.print_error(
                        self.translator.get("database.docker_cp_failed", error=copy_result.stderr.strip())
                    )
                return False

            # Cleanup temp file in container
            if container_id:
                subprocess.run(["docker", "exec", container_id, "rm", "-f", container_dump], capture_output=True, timeout=10)
            else:
                subprocess.run(
                    ["docker", "compose"] + f_args + ["exec", "-T", service_name, "rm", "-f", container_dump],
                    cwd=cwd, capture_output=True, timeout=10
                )

            return backup_file.exists() and backup_file.stat().st_size > 0

        except Exception as e:
            formatter.print_error(
                self.translator.get("database.docker_backup_exception", error=str(e))
            )
            return False
    
    def restore(self, service_name: str, environment: str, database: str, username: str, backup_path: Path, formatter) -> bool:
        """Restore using pg_restore in Docker container."""
        compose_files = get_compose_file_list(self.project_root, environment, self.docker_compose_config)
        if not compose_files:
            formatter.print_error(self.translator.get("database.docker_compose_not_found"))
            return False
        cwd = get_compose_cwd(compose_files[0], self.docker_compose_config)
        f_args = self._compose_f_args(compose_files)

        try:
            # Check if service is running, if not - try to start it
            container_id = None
            check_cmd = ["docker", "compose"] + f_args + ["ps", "--status", "running", "-q", service_name]
            check_result = subprocess.run(
                check_cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if check_result.returncode != 0 or not check_result.stdout.strip():
                ok, container_id = self._start_service(compose_files, cwd, service_name, formatter)
                if not ok:
                    formatter.print_error(self.translator.get("database.docker_service_start_hint"))
                    return False

            # Create temp file inside container
            container_dump = f"/tmp/restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dump"

            # Copy backup file to container
            if container_id:
                copy_cmd = ["docker", "cp", str(backup_path), f"{container_id}:{container_dump}"]
                copy_result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=60)
            else:
                copy_cmd = ["docker", "compose"] + f_args + ["cp", str(backup_path), f"{service_name}:{container_dump}"]
                copy_result = subprocess.run(copy_cmd, cwd=cwd, capture_output=True, text=True, timeout=60)

            if copy_result.returncode != 0:
                if copy_result.stderr:
                    formatter.print_error(
                        self.translator.get("database.docker_cp_failed", error=copy_result.stderr.strip())
                    )
                return False

            # Execute pg_restore inside container
            # Use -h 127.0.0.1 to force IPv4 TCP connection (IPv6 ::1 may not be allowed in pg_hba.conf)
            if container_id:
                cmd = ["docker", "exec", container_id, "pg_restore", "-h", "127.0.0.1", "-U", username, "-d", database,
                       "--clean", "--if-exists", "--disable-triggers", "--no-owner", "--no-acl", container_dump]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            else:
                cmd = [
                    "docker", "compose"] + f_args + [
                    "exec", "-T", service_name,
                    "pg_restore", "-h", "127.0.0.1", "-U", username, "-d", database,
                    "--clean", "--if-exists", "--disable-triggers", "--no-owner", "--no-acl", container_dump,
                ]
                result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)

            # Cleanup temp file in container
            if container_id:
                subprocess.run(["docker", "exec", container_id, "rm", "-f", container_dump], capture_output=True, timeout=10)
            else:
                subprocess.run(
                    ["docker", "compose"] + f_args + ["exec", "-T", service_name, "rm", "-f", container_dump],
                    cwd=cwd, capture_output=True, timeout=10
                )
            
            if result.returncode == 0:
                formatter.print_success(
                    f"✓ {self.translator.get('database.restore_success')}: {backup_path.name}"
                )
                return True
            
            stderr = result.stderr or ""
            if "errors ignored on restore" in stderr:
                formatter.print_warning(
                    f"⚠ {self.translator.get('database.restore_completed_with_warnings')}: {backup_path.name}\n{stderr}"
                )
                return True
            
            if stderr:
                formatter.print_error(
                    self.translator.get("database.docker_pg_restore_failed", error=stderr.strip())
                )
            return False
            
        except Exception as e:
            formatter.print_error(
                self.translator.get("database.docker_restore_exception", error=str(e))
            )
            return False

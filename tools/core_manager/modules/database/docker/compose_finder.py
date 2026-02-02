"""Docker Compose file finder utility."""

import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional


def _get_global_config_dir(docker_compose_config: dict) -> Path:
    """Return resolved global config directory path from config."""
    global_config_dir_str = docker_compose_config.get("global_config_dir", "~/.coreness")
    return Path(os.path.expanduser(global_config_dir_str))


def get_compose_cwd(compose_file: Path, docker_compose_config: dict) -> Path:
    """Return working directory for docker compose so project name matches. Prefer global config dir when compose is there."""
    global_config_dir = _get_global_config_dir(docker_compose_config)
    try:
        compose_file.resolve().relative_to(global_config_dir.resolve())
        return global_config_dir
    except ValueError:
        return compose_file.parent


def find_compose_file(project_root: Path, environment: str, docker_compose_config: dict) -> Optional[Path]:
    """Find docker-compose file for given environment.
    
    Search order:
    1. Global config dir (used by dc command)
    2. Project root
    3. Project docker/ subdirectory
    """
    global_config_dir = _get_global_config_dir(docker_compose_config)
    
    compose_files = [
        # Global config (used by dc command)
        global_config_dir / f"docker-compose.{environment}.yml",
        global_config_dir / "docker-compose.yml",
        # Project root
        project_root / f"docker-compose.{environment}.yml",
        project_root / "docker-compose.yml",
        # Project docker/ subdirectory
        project_root / "docker" / f"docker-compose.{environment}.yml",
        project_root / "docker" / "docker-compose.yml",
    ]
    
    for compose_file in compose_files:
        if compose_file.exists():
            return compose_file
    
    return None


def get_compose_file_list(project_root: Path, environment: str, docker_compose_config: dict) -> List[Path]:
    """Return list of compose files in order: main file and override if it exists (so resource limits from ~/.coreness are applied)."""
    compose_file = find_compose_file(project_root, environment, docker_compose_config)
    if not compose_file:
        return []
    cwd = get_compose_cwd(compose_file, docker_compose_config)
    override_path = cwd / f"docker-compose.override-{environment}.yml"
    result = [compose_file]
    if override_path.exists():
        result.append(override_path)
    return result


def get_postgres_service_name_from_config(project_root: Path, environment: str, docker_compose_config: dict) -> Optional[str]:
    """Get PostgreSQL service name from docker-compose config (doesn't check if running)."""
    compose_file = find_compose_file(project_root, environment, docker_compose_config)
    if not compose_file:
        return None
    
    try:
        import yaml
        
        with open(compose_file, 'r', encoding='utf-8') as f:
            compose_config = yaml.safe_load(f)
        
        services = compose_config.get('services', {})
        
        # Look for postgres service (common names)
        postgres_names = [f'postgres-{environment}', 'postgres', 'db', 'database']
        for name in postgres_names:
            if name in services:
                return name
        
        return None
    except Exception:
        return None


def get_postgres_service_name(project_root: Path, environment: str, docker_compose_config: dict) -> Optional[str]:
    """Get PostgreSQL service name from docker-compose config and verify it's running."""
    service_name = get_postgres_service_name_from_config(project_root, environment, docker_compose_config)
    if not service_name:
        return None
    
    compose_files = get_compose_file_list(project_root, environment, docker_compose_config)
    if not compose_files:
        return None
    
    cwd = get_compose_cwd(compose_files[0], docker_compose_config)
    if _is_service_running(compose_files, service_name, cwd):
        return service_name
    
    return None


def postgres_container_exists(project_root: Path, environment: str, docker_compose_config: dict) -> bool:
    """Return True if PostgreSQL container exists (running or stopped). Uses docker ps so result does not depend on compose project path."""
    service_name = get_postgres_service_name_from_config(project_root, environment, docker_compose_config)
    if not service_name:
        return False
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "--filter", f"name={service_name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and bool(result.stdout and result.stdout.strip())
    except Exception:
        return False


def ensure_postgres_container_running(project_root: Path, environment: str, docker_compose_config: dict) -> bool:
    """Create and start PostgreSQL container if it does not exist. Returns True on success."""
    compose_files = get_compose_file_list(project_root, environment, docker_compose_config)
    if not compose_files:
        return False
    service_name = get_postgres_service_name_from_config(project_root, environment, docker_compose_config)
    if not service_name:
        return False
    cwd = get_compose_cwd(compose_files[0], docker_compose_config)
    if _is_service_running(compose_files, service_name, cwd):
        return True
    try:
        f_args = [arg for f in compose_files for arg in ("-f", str(f))]
        result = subprocess.run(
            ["docker", "compose"] + f_args + ["up", "-d", service_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return False
        for _ in range(15):
            if _is_service_running(compose_files, service_name, cwd):
                return True
            time.sleep(1)
        return False
    except Exception:
        return False


def _is_service_running(compose_files: List[Path], service_name: str, cwd: Path) -> bool:
    """Check if a docker compose service is running."""
    try:
        f_args = [arg for f in compose_files for arg in ("-f", str(f))]
        # First try: check service status with ps --status=running
        result = subprocess.run(
            ["docker", "compose"] + f_args + ["ps", "--status", "running", "-q", service_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return True
        
        # Fallback: check if container exists and inspect its state
        result = subprocess.run(
            ["docker", "compose"] + f_args + ["ps", "-q", service_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            container_id = result.stdout.strip()
            # Check container state with docker inspect
            inspect_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            return inspect_result.returncode == 0 and inspect_result.stdout.strip().lower() == "true"
        
        return False
    except Exception:
        return False

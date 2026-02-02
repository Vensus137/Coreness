"""Restart and resume: one place for restart-with-args, marker files, and dispatch after restart.

- restart() / restart_with_resume(): run utility again with given args; restart_with_resume writes a marker so the new process can resume even when argv is not passed (e.g. Windows new console).
- register_resume(): register a handler for a resume argument (e.g. --resume-update).
- handle_resume(): on startup, read markers and argv, dispatch to the registered handler or return without running anything.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional


class RestartManager:
    """Restart utility and resume flows: markers, args, and handler dispatch."""

    def __init__(self, utility_root: Path, project_root: Path):
        self.utility_root = Path(utility_root)
        self.project_root = Path(project_root)
        self.script_path = self.utility_root / "core_manager.py"
        self._resume_handlers: Dict[str, Callable] = {}

    def _marker_path(self, resume_arg: str) -> Path:
        """Path for marker file: .core_manager_<arg_without_leading_dashes_with_underscores>."""
        name = resume_arg.lstrip("-").replace("-", "_")
        return self.project_root / f".core_manager_{name}"

    def restart(self, args: Optional[List[str]] = None, exit_after: bool = True) -> None:
        """Restart utility with optional arguments."""
        if args is None:
            args = []

        if exit_after:
            if sys.platform == "win32":
                cmd = [sys.executable, str(self.script_path)] + args
                kwargs = {"cwd": str(self.project_root)}
                if hasattr(subprocess, "CREATE_NEW_CONSOLE"):
                    kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                subprocess.Popen(cmd, **kwargs)
                sys.exit(0)
            else:
                os.chdir(str(self.project_root))
                os.execv(sys.executable, [sys.executable, str(self.script_path)] + args)
        else:
            cmd = [sys.executable, str(self.script_path)] + args
            subprocess.Popen(cmd, cwd=str(self.project_root))

    def restart_with_resume(self, resume_arg: str, exit_after: bool = True) -> None:
        """Write marker for resume_arg and restart so the new process can run the matching handler (argv may be missing on Windows)."""
        marker = self._marker_path(resume_arg)
        try:
            marker.touch()
        except Exception:
            pass
        self.restart(args=[resume_arg], exit_after=exit_after)

    def register_resume(self, resume_arg: str, handler: Callable) -> None:
        """Register handler(argv) for this resume argument."""
        self._resume_handlers[resume_arg] = handler

    def handle_resume(self, argv: list) -> bool:
        """If a resume marker or argv is present, run the registered handler and return True; otherwise return False."""
        for resume_arg, handler in self._resume_handlers.items():
            marker = self._marker_path(resume_arg)
            if marker.exists():
                try:
                    marker.unlink()
                except Exception:
                    pass
                if resume_arg not in argv:
                    argv.append(resume_arg)

        for resume_arg, handler in self._resume_handlers.items():
            if resume_arg not in argv:
                continue
            while resume_arg in argv:
                argv.remove(resume_arg)
            handler(argv)
            self._fix_stdin_after_restart()
            return True
        return False

    def _fix_stdin_after_restart(self) -> None:
        """Flush streams and clear keyboard buffer after execv restart."""
        sys.stdin.flush()
        sys.stdout.flush()
        sys.stderr.flush()
        if sys.platform == "win32":
            time.sleep(0.5)
            try:
                import msvcrt
                while msvcrt.kbhit():
                    msvcrt.getch()
            except ImportError:
                pass

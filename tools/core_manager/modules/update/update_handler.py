"""Update handler - manages self-update UI flow."""

from ..ui.colors import Colors
from ..ui.dialogs import confirm
from .self_updater import SelfUpdater
from .version_fetcher import version_gt


def _norm(v: str) -> str:
    """Normalize version for comparison (strip v prefix)."""
    return (v or "").lstrip("v").strip()


def _display_version(v: str) -> str:
    """Return version with v prefix for display."""
    return v if (v or "").startswith("v") else f"v{v}"


class UpdateHandler:
    """Handles self-update user interface and flow."""

    def __init__(self, self_updater: SelfUpdater, translator):
        self.updater = self_updater
        self.t = translator

    def handle_update(self) -> None:
        """Handle complete self-update flow with user interaction."""
        try:
            deps = self.updater.config.get('dependencies', [])
            if deps:
                from ..core.dependencies import ensure_dependencies
                if not ensure_dependencies(deps, self.t):
                    print(Colors.error(self.t.get('self_update.dependencies_missing')))
                    return

            print(Colors.info(f"\n{self.t.get('self_update.checking')}"))

            info = self.updater.check_for_updates()
            if not info:
                return

            current = info["current"]
            latest_stable = info.get("latest_stable")
            latest_prerelease = info.get("latest_prerelease")
            current_norm = _norm(current) if current != "unknown" else ""

            if not latest_stable and not latest_prerelease:
                print(Colors.error(self.t.get('self_update.no_version')))
                return

            # Choose target: prerelease is optional when it's newer than stable
            target = None
            if latest_prerelease and (not latest_stable or version_gt(latest_prerelease, latest_stable)):
                # Pre-release is available and newer than stable: ask
                print(f"{self.t.get('self_update.current')}: {Colors.unknown(current) if current == 'unknown' else Colors.version(_display_version(current_norm))}")
                print(f"{self.t.get('self_update.latest_stable')}: {Colors.version(_display_version(latest_stable)) if latest_stable else Colors.version('—')}")
                print(f"{self.t.get('self_update.latest_prerelease')}: {Colors.version(_display_version(latest_prerelease))}")
                msg = self.t.get('self_update.confirm_prerelease', version=_display_version(latest_prerelease))
                if confirm(msg, default=False, translator=self.t):
                    target = latest_prerelease
                else:
                    target = latest_stable
                    if not target:
                        print(Colors.info(self.t.get('self_update.no_stable_release')))
                        return
            else:
                target = latest_stable or latest_prerelease
                print(f"{self.t.get('self_update.current')}: {Colors.unknown(current) if current == 'unknown' else Colors.version(_display_version(current_norm))}")
                print(f"{self.t.get('self_update.latest')}: {Colors.version(_display_version(target))}")

            if not target:
                print(Colors.error(self.t.get('self_update.no_version')))
                return

            if current_norm and _norm(target) == current_norm:
                print(Colors.success(f"\n✓ {self.t.get('self_update.up_to_date')}"))
                return

            print(Colors.warning(f"\n{self.t.get('self_update.update_available')}"))
            message = f"{self.t.get('self_update.confirm')} {Colors.version(_display_version(target))}?"
            if not confirm(message, default=True, translator=self.t):
                print(Colors.info(self.t.get('messages.cancelled')))
                return

            self.updater.perform_update(target)

        except KeyboardInterrupt:
            print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
        except Exception as e:
            print(Colors.error(f"\n{self.t.get('self_update.failed')}: {e}"))

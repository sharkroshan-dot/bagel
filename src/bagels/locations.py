from pathlib import Path
from typing import Optional
from xdg_base_dirs import xdg_config_home, xdg_data_home

# Store the custom root directory
_custom_root: Optional[Path] = None


def set_custom_root(path: Optional[str | Path]) -> None:
    """Set a custom root directory for all app files."""
    global _custom_root
    _custom_root = Path(path) if path else None


def _app_directory(root: Path) -> Path:
    """Create and return the application directory."""
    if _custom_root is not None:
        directory = _custom_root
    else:
        directory = root / "bagels"

    directory.mkdir(exist_ok=True, parents=True)
    return directory


def data_directory() -> Path:
    """Return (possibly creating) the application data directory."""
    return _app_directory(xdg_data_home())


def config_directory() -> Path:
    """Return (possibly creating) the application config directory."""
    return _app_directory(xdg_config_home())


def config_file() -> Path:
    return config_directory() / "config.yaml"


def database_file() -> Path:
    return data_directory() / "db.db"

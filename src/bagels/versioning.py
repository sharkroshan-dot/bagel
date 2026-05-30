import requests
from packaging import version
from importlib.metadata import metadata


def get_pypi_version():
    """Fetch the latest version from PyPI."""
    try:
        response = requests.get("https://pypi.org/pypi/bagels/json")
        return response.json()["info"]["version"]
    except Exception:
        return None


def get_current_version():
    return metadata("bagels")["Version"]


def needs_update():
    """Check if the current version needs an update."""
    pypi_version = get_pypi_version()
    current_version = get_current_version()
    if not pypi_version:
        return False

    return version.parse(pypi_version) > version.parse(current_version)

"""Platform adaptation module for cross-platform compatibility."""
import sys
from typing import Type

from .base import PlatformAdapter


def get_platform_adapter() -> Type[PlatformAdapter]:
    """Get the appropriate platform adapter based on the current OS."""
    # Import platform module carefully to avoid conflicts
    import platform as std_platform
    system = std_platform.system().lower()
    
    if system == "darwin":
        from .macos import MacOSAdapter
        return MacOSAdapter
    elif system == "linux":
        from .linux import LinuxAdapter
        return LinuxAdapter
    elif system == "windows":
        from .windows import WindowsAdapter
        return WindowsAdapter
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


__all__ = ["PlatformAdapter", "get_platform_adapter"]

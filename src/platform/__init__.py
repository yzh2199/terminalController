"""Platform adaptation module for cross-platform compatibility."""
import sys
from typing import Type

from .base import PlatformAdapter


def _normalize_sys_platform() -> str:
    """Normalize sys.platform to 'darwin' | 'linux' | 'windows'."""
    p = sys.platform.lower()
    if p.startswith("darwin") or p == "mac" or p == "macos":
        return "darwin"
    if p.startswith("linux"):
        return "linux"
    if p.startswith("win"):
        return "windows"
    return p


def get_platform_adapter() -> Type[PlatformAdapter]:
    """Get the appropriate platform adapter based on the current OS.

    Avoid importing stdlib 'platform' to prevent name collision with local package 'platform'.
    """
    system = _normalize_sys_platform()
    
    if system == "darwin":
        # Use optimized macOS adapter globally for better performance
        from .macos_optimized import OptimizedMacOSAdapter
        return OptimizedMacOSAdapter
    elif system == "linux":
        from .linux import LinuxAdapter
        return LinuxAdapter
    elif system == "windows":
        from .windows import WindowsAdapter
        return WindowsAdapter
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


__all__ = ["PlatformAdapter", "get_platform_adapter"]

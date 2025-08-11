"""Unit tests for platform base classes."""
import pytest
from unittest.mock import Mock

from src.platform.base import PlatformAdapter, WindowInfo, AppInfo


class TestWindowInfo:
    """Test cases for WindowInfo class."""
    
    def test_window_info_creation(self):
        """Test WindowInfo creation with all parameters."""
        window = WindowInfo(
            window_id="12345",
            title="Test Window",
            app_name="Test App",
            is_active=True,
            is_minimized=False,
            position=(100, 200),
            size=(800, 600)
        )
        
        assert window.window_id == "12345"
        assert window.title == "Test Window"
        assert window.app_name == "Test App"
        assert window.is_active is True
        assert window.is_minimized is False
        assert window.position == (100, 200)
        assert window.size == (800, 600)
    
    def test_window_info_defaults(self):
        """Test WindowInfo default values."""
        window = WindowInfo(
            window_id="12345",
            title="Test Window",
            app_name="Test App",
            is_active=True,
            is_minimized=False
        )
        
        assert window.position == (0, 0)
        assert window.size == (0, 0)


class TestAppInfo:
    """Test cases for AppInfo class."""
    
    def test_app_info_creation(self):
        """Test AppInfo creation with windows."""
        windows = [
            WindowInfo(
                window_id="1",
                title="Window 1",
                app_name="Test App",
                is_active=True,
                is_minimized=False
            ),
            WindowInfo(
                window_id="2",
                title="Window 2",
                app_name="Test App",
                is_active=False,
                is_minimized=True
            )
        ]
        
        app = AppInfo(
            pid=1234,
            name="Test App",
            executable_path="/path/to/app",
            windows=windows
        )
        
        assert app.pid == 1234
        assert app.name == "Test App"
        assert app.executable_path == "/path/to/app"
        assert len(app.windows) == 2
        assert app.windows[0].window_id == "1"
        assert app.windows[1].window_id == "2"
    
    def test_app_info_empty_windows(self):
        """Test AppInfo creation with empty windows list."""
        app = AppInfo(
            pid=1234,
            name="Test App",
            executable_path="/path/to/app",
            windows=[]
        )
        
        assert len(app.windows) == 0


class TestPlatformAdapter:
    """Test cases for PlatformAdapter abstract base class."""
    
    def test_platform_adapter_is_abstract(self):
        """Test that PlatformAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PlatformAdapter()
    
    def test_platform_adapter_methods_are_abstract(self):
        """Test that all required methods are abstract."""
        # Create a concrete implementation that doesn't implement all methods
        class IncompleteAdapter(PlatformAdapter):
            def launch_app(self, app_path, args=None, cwd=None):
                return True
        
        # Should still raise TypeError because not all methods are implemented
        with pytest.raises(TypeError):
            IncompleteAdapter()
    
    def test_platform_adapter_full_implementation(self):
        """Test that a complete implementation can be instantiated."""
        class CompleteAdapter(PlatformAdapter):
            def launch_app(self, app_path, args=None, cwd=None):
                return True
            
            def get_running_apps(self, app_name=None):
                return []
            
            def get_app_windows(self, app_name):
                return []
            
            def activate_window(self, window_id):
                return True
            
            def minimize_window(self, window_id):
                return True
            
            def close_window(self, window_id):
                return True
            
            def register_hotkey(self, hotkey, callback):
                return True
            
            def unregister_hotkey(self, hotkey):
                return True
            
            def get_active_window(self):
                return None
            
            def is_app_running(self, app_name):
                return False
            
            def kill_app(self, app_name, force=False):
                return True
            
            def open_url(self, url, browser_path=None):
                return True
            
            def get_default_terminal(self):
                return "terminal"
            
            def normalize_app_path(self, app_path):
                return app_path
        
        # Should be able to instantiate complete implementation
        adapter = CompleteAdapter()
        assert adapter is not None
        
        # Test that methods can be called
        assert adapter.launch_app("/path/to/app") is True
        assert adapter.get_running_apps() == []
        assert adapter.activate_window("123") is True
        assert adapter.is_app_running("test") is False


class MockPlatformAdapter(PlatformAdapter):
    """Mock implementation of PlatformAdapter for testing."""
    
    def __init__(self):
        self.launched_apps = []
        self.running_apps = []
        self.windows = {}
        self.hotkeys = {}
        self.active_window = None
    
    def launch_app(self, app_path, args=None, cwd=None):
        self.launched_apps.append({
            'app_path': app_path,
            'args': args or [],
            'cwd': cwd
        })
        return True
    
    def get_running_apps(self, app_name=None):
        if app_name:
            return [app for app in self.running_apps if app_name.lower() in app.name.lower()]
        return self.running_apps
    
    def get_app_windows(self, app_name):
        return self.windows.get(app_name, [])
    
    def activate_window(self, window_id):
        # Find and activate window
        for windows in self.windows.values():
            for window in windows:
                if window.window_id == window_id:
                    window.is_active = True
                    self.active_window = window
                    return True
                else:
                    window.is_active = False
        return False
    
    def minimize_window(self, window_id):
        # Find and minimize window
        for windows in self.windows.values():
            for window in windows:
                if window.window_id == window_id:
                    window.is_minimized = True
                    return True
        return False
    
    def close_window(self, window_id):
        # Find and remove window
        for app_name, windows in self.windows.items():
            for i, window in enumerate(windows):
                if window.window_id == window_id:
                    del windows[i]
                    return True
        return False
    
    def register_hotkey(self, hotkey, callback):
        self.hotkeys[hotkey] = callback
        return True
    
    def unregister_hotkey(self, hotkey):
        if hotkey in self.hotkeys:
            del self.hotkeys[hotkey]
            return True
        return False
    
    def get_active_window(self):
        return self.active_window
    
    def is_app_running(self, app_name):
        return any(app_name.lower() in app.name.lower() for app in self.running_apps)
    
    def kill_app(self, app_name, force=False):
        self.running_apps = [app for app in self.running_apps 
                           if app_name.lower() not in app.name.lower()]
        return True
    
    def open_url(self, url, browser_path=None):
        return True
    
    def get_default_terminal(self):
        return "mock-terminal"
    
    def normalize_app_path(self, app_path):
        return app_path


class TestMockPlatformAdapter:
    """Test cases for MockPlatformAdapter."""
    
    def test_mock_adapter_initialization(self):
        """Test MockPlatformAdapter initialization."""
        adapter = MockPlatformAdapter()
        
        assert adapter.launched_apps == []
        assert adapter.running_apps == []
        assert adapter.windows == {}
        assert adapter.hotkeys == {}
        assert adapter.active_window is None
    
    def test_launch_app_tracking(self):
        """Test that launch_app tracks launched applications."""
        adapter = MockPlatformAdapter()
        
        adapter.launch_app("/path/to/app", args=["--test"], cwd="/home")
        
        assert len(adapter.launched_apps) == 1
        launched = adapter.launched_apps[0]
        assert launched['app_path'] == "/path/to/app"
        assert launched['args'] == ["--test"]
        assert launched['cwd'] == "/home"
    
    def test_window_management(self):
        """Test window management functionality."""
        adapter = MockPlatformAdapter()
        
        # Add some test windows
        windows = [
            WindowInfo("1", "Window 1", "Test App", False, False),
            WindowInfo("2", "Window 2", "Test App", False, False)
        ]
        adapter.windows["Test App"] = windows
        
        # Test getting windows
        app_windows = adapter.get_app_windows("Test App")
        assert len(app_windows) == 2
        
        # Test activating window
        assert adapter.activate_window("1") is True
        assert windows[0].is_active is True
        assert windows[1].is_active is False
        assert adapter.active_window == windows[0]
        
        # Test minimizing window
        assert adapter.minimize_window("2") is True
        assert windows[1].is_minimized is True
        
        # Test closing window
        assert adapter.close_window("1") is True
        assert len(adapter.windows["Test App"]) == 1
    
    def test_hotkey_management(self):
        """Test hotkey registration and unregistration."""
        adapter = MockPlatformAdapter()
        
        def test_callback():
            pass
        
        # Test registering hotkey
        assert adapter.register_hotkey("ctrl+t", test_callback) is True
        assert "ctrl+t" in adapter.hotkeys
        assert adapter.hotkeys["ctrl+t"] == test_callback
        
        # Test unregistering hotkey
        assert adapter.unregister_hotkey("ctrl+t") is True
        assert "ctrl+t" not in adapter.hotkeys
        
        # Test unregistering non-existent hotkey
        assert adapter.unregister_hotkey("ctrl+x") is False
    
    def test_app_running_status(self):
        """Test checking if applications are running."""
        adapter = MockPlatformAdapter()
        
        # Add running app
        app_info = AppInfo(1234, "Test App", "/path/to/app", [])
        adapter.running_apps.append(app_info)
        
        # Test checking running status
        assert adapter.is_app_running("Test App") is True
        assert adapter.is_app_running("Other App") is False
        
        # Test killing app
        assert adapter.kill_app("Test App") is True
        assert adapter.is_app_running("Test App") is False

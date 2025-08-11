"""Unit tests for AppManager module."""
import pytest
from unittest.mock import Mock, patch, call
from pathlib import Path

from src.app_manager import AppManager
from src.config_manager import ConfigManager, AppConfig
from src.platform.base import WindowInfo, AppInfo


class TestAppManager:
    """Test cases for AppManager class."""
    
    @pytest.fixture
    def app_manager(self, config_manager, mock_platform_adapter):
        """Create AppManager instance with mocked dependencies."""
        with patch('src.app_manager.get_platform_adapter') as mock_get_adapter:
            mock_get_adapter.return_value = lambda: mock_platform_adapter
            
            app_manager = AppManager(config_manager)
            app_manager.platform_adapter = mock_platform_adapter
            return app_manager
    
    def test_init(self, config_manager, mock_platform_adapter):
        """Test AppManager initialization."""
        with patch('src.app_manager.get_platform_adapter') as mock_get_adapter:
            mock_get_adapter.return_value = lambda: mock_platform_adapter
            
            app_manager = AppManager(config_manager)
            
            assert app_manager.config_manager == config_manager
            assert app_manager.platform_adapter == mock_platform_adapter
            assert app_manager.current_platform == 'darwin'
    
    def test_launch_app_success(self, app_manager, mock_platform_adapter):
        """Test successful application launch."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager.launch_app('test_app')
        
        assert success is True
        mock_platform_adapter.launch_app.assert_called_once()
    
    def test_launch_app_unknown(self, app_manager, mock_platform_adapter):
        """Test launching unknown application."""
        success = app_manager.launch_app('unknown_app')
        
        assert success is False
        mock_platform_adapter.launch_app.assert_not_called()
    
    def test_launch_app_with_website(self, app_manager, mock_platform_adapter):
        """Test launching application with website."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager.launch_app('test_browser', website_id='test_site')
        
        assert success is True
        mock_platform_adapter.launch_app.assert_called_once()
    
    def test_launch_app_with_url(self, app_manager, mock_platform_adapter):
        """Test launching application with direct URL."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager.launch_app('test_browser', url='https://example.com')
        
        assert success is True
        mock_platform_adapter.launch_app.assert_called_once()
    
    def test_launch_app_force_new(self, app_manager, mock_platform_adapter):
        """Test launching application with force new window."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager.launch_app('test_app', force_new=True)
        
        assert success is True
        # Verify that --new-window is in the arguments
        call_args = mock_platform_adapter.launch_app.call_args
        args = call_args[1].get('args', [])
        assert '--new-window' in args
    
    def test_launch_app_platform_failure(self, app_manager, mock_platform_adapter):
        """Test application launch platform failure."""
        mock_platform_adapter.launch_app.return_value = False
        
        success = app_manager.launch_app('test_app')
        
        assert success is False
    
    def test_get_app_windows(self, app_manager, mock_platform_adapter, sample_window_info):
        """Test getting application windows."""
        mock_platform_adapter.get_app_windows.return_value = sample_window_info
        
        windows = app_manager.get_app_windows('test_app')
        
        assert len(windows) == 2
        assert windows[0].window_id == "12345"
        assert windows[1].window_id == "67890"
        mock_platform_adapter.get_app_windows.assert_called_once_with('Test Application')
    
    def test_get_app_windows_unknown_app(self, app_manager, mock_platform_adapter):
        """Test getting windows for unknown application."""
        windows = app_manager.get_app_windows('unknown_app')
        
        assert windows == []
        mock_platform_adapter.get_app_windows.assert_not_called()
    
    def test_activate_window_by_id(self, app_manager, mock_platform_adapter):
        """Test activating window by specific ID."""
        mock_platform_adapter.activate_window.return_value = True
        
        success = app_manager.activate_window('test_app', window_id='12345')
        
        assert success is True
        mock_platform_adapter.activate_window.assert_called_once_with('12345')
    
    def test_activate_window_auto_select(self, app_manager, mock_platform_adapter, sample_window_info):
        """Test activating window with auto-selection."""
        mock_platform_adapter.get_app_windows.return_value = sample_window_info
        mock_platform_adapter.activate_window.return_value = True
        
        success = app_manager.activate_window('test_app')
        
        assert success is True
        # Should activate the active window (first one)
        mock_platform_adapter.activate_window.assert_called_once_with('12345')
    
    def test_activate_window_no_windows(self, app_manager, mock_platform_adapter):
        """Test activating window when no windows exist."""
        mock_platform_adapter.get_app_windows.return_value = []
        
        success = app_manager.activate_window('test_app')
        
        assert success is False
        mock_platform_adapter.activate_window.assert_not_called()
    
    def test_minimize_window_by_id(self, app_manager, mock_platform_adapter):
        """Test minimizing window by specific ID."""
        mock_platform_adapter.minimize_window.return_value = True
        
        success = app_manager.minimize_window('test_app', window_id='12345')
        
        assert success is True
        mock_platform_adapter.minimize_window.assert_called_once_with('12345')
    
    def test_minimize_window_all(self, app_manager, mock_platform_adapter, sample_window_info):
        """Test minimizing all windows for an application."""
        mock_platform_adapter.get_app_windows.return_value = sample_window_info
        mock_platform_adapter.minimize_window.return_value = True
        
        success = app_manager.minimize_window('test_app')
        
        assert success is True
        # Should call minimize for each window
        assert mock_platform_adapter.minimize_window.call_count == 2
        mock_platform_adapter.minimize_window.assert_any_call('12345')
        mock_platform_adapter.minimize_window.assert_any_call('67890')
    
    def test_close_window_by_id(self, app_manager, mock_platform_adapter):
        """Test closing window by specific ID."""
        mock_platform_adapter.close_window.return_value = True
        
        success = app_manager.close_window('test_app', window_id='12345')
        
        assert success is True
        mock_platform_adapter.close_window.assert_called_once_with('12345')
    
    def test_close_window_all(self, app_manager, mock_platform_adapter, sample_window_info):
        """Test closing all windows for an application."""
        mock_platform_adapter.get_app_windows.return_value = sample_window_info
        mock_platform_adapter.close_window.return_value = True
        
        success = app_manager.close_window('test_app')
        
        assert success is True
        # Should call close for each window
        assert mock_platform_adapter.close_window.call_count == 2
        mock_platform_adapter.close_window.assert_any_call('12345')
        mock_platform_adapter.close_window.assert_any_call('67890')
    
    def test_is_app_running_true(self, app_manager, mock_platform_adapter):
        """Test checking if application is running (true case)."""
        mock_platform_adapter.is_app_running.return_value = True
        
        running = app_manager.is_app_running('test_app')
        
        assert running is True
        mock_platform_adapter.is_app_running.assert_called_once_with('Test Application')
    
    def test_is_app_running_false(self, app_manager, mock_platform_adapter):
        """Test checking if application is running (false case)."""
        mock_platform_adapter.is_app_running.return_value = False
        
        running = app_manager.is_app_running('test_app')
        
        assert running is False
    
    def test_is_app_running_unknown_app(self, app_manager, mock_platform_adapter):
        """Test checking if unknown application is running."""
        running = app_manager.is_app_running('unknown_app')
        
        assert running is False
        mock_platform_adapter.is_app_running.assert_not_called()
    
    def test_kill_app_success(self, app_manager, mock_platform_adapter):
        """Test killing application successfully."""
        mock_platform_adapter.kill_app.return_value = True
        
        success = app_manager.kill_app('test_app')
        
        assert success is True
        mock_platform_adapter.kill_app.assert_called_once_with('Test Application', False)
    
    def test_kill_app_force(self, app_manager, mock_platform_adapter):
        """Test force killing application."""
        mock_platform_adapter.kill_app.return_value = True
        
        success = app_manager.kill_app('test_app', force=True)
        
        assert success is True
        mock_platform_adapter.kill_app.assert_called_once_with('Test Application', True)
    
    def test_kill_app_unknown(self, app_manager, mock_platform_adapter):
        """Test killing unknown application."""
        success = app_manager.kill_app('unknown_app')
        
        assert success is False
        mock_platform_adapter.kill_app.assert_not_called()
    
    def test_open_url_default_browser(self, app_manager, mock_platform_adapter):
        """Test opening URL with default browser."""
        mock_platform_adapter.open_url.return_value = True
        
        success = app_manager.open_url('https://example.com')
        
        assert success is True
        mock_platform_adapter.open_url.assert_called_once_with('https://example.com', None)
    
    def test_open_url_specific_browser(self, app_manager, mock_platform_adapter):
        """Test opening URL with specific browser."""
        mock_platform_adapter.open_url.return_value = True
        
        success = app_manager.open_url('https://example.com', app_id='test_browser')
        
        assert success is True
        # Should be called with the browser executable path
        call_args = mock_platform_adapter.open_url.call_args[0]
        assert call_args[0] == 'https://example.com'
        assert call_args[1] is not None  # Browser path should be provided
    
    def test_get_running_apps(self, app_manager, mock_platform_adapter, sample_app_info):
        """Test getting running applications."""
        mock_platform_adapter.get_running_apps.return_value = [sample_app_info]
        
        apps = app_manager.get_running_apps()
        
        assert len(apps) == 1
        assert apps[0].name == 'Test App'
        assert apps[0].pid == 1234
    
    def test_select_window_interactive_single(self, app_manager, sample_window_info):
        """Test interactive window selection with single window."""
        single_window = [sample_window_info[0]]
        
        selected = app_manager.select_window_interactive(single_window)
        
        assert selected == sample_window_info[0]
    
    def test_select_window_interactive_none(self, app_manager):
        """Test interactive window selection with no windows."""
        selected = app_manager.select_window_interactive([])
        
        assert selected is None
    
    @patch('builtins.input', return_value='2')
    def test_select_window_interactive_multiple(self, mock_input, app_manager, sample_window_info):
        """Test interactive window selection with multiple windows."""
        selected = app_manager.select_window_interactive(sample_window_info)
        
        assert selected == sample_window_info[1]  # Second window (index 1)
    
    @patch('builtins.input', return_value='')
    def test_select_window_interactive_default(self, mock_input, app_manager, sample_window_info):
        """Test interactive window selection with default choice."""
        selected = app_manager.select_window_interactive(sample_window_info)
        
        assert selected == sample_window_info[0]  # First window (default)
    
    @patch('builtins.input', return_value='invalid')
    def test_select_window_interactive_invalid(self, mock_input, app_manager, sample_window_info):
        """Test interactive window selection with invalid input."""
        selected = app_manager.select_window_interactive(sample_window_info)
        
        assert selected == sample_window_info[0]  # First window (fallback)
    
    def test_get_executable_path_macos(self, app_manager):
        """Test getting executable path for macOS."""
        app_config = AppConfig(
            name='Test App',
            executable={
                'macos': '/Applications/TestApp.app',
                'linux': 'test-app',
                'windows': 'testapp.exe'
            },
            type='test'
        )
        
        path = app_manager._get_executable_path(app_config)
        assert path == '/Applications/TestApp.app'
    
    def test_get_executable_path_fallback(self, app_manager):
        """Test getting executable path with fallback."""
        app_config = AppConfig(
            name='Test App',
            executable={
                'linux': 'test-app',
                'default': '/default/path/to/app'
            },
            type='test'
        )
        
        path = app_manager._get_executable_path(app_config)
        assert path == '/default/path/to/app'
    
    def test_get_executable_path_not_found(self, app_manager):
        """Test getting executable path when not found."""
        app_config = AppConfig(
            name='Test App',
            executable={
                'linux': 'test-app',
                'windows': 'testapp.exe'
            },
            type='test'
        )
        
        path = app_manager._get_executable_path(app_config)
        assert path is None
    
    def test_get_target_window_active(self, app_manager, mock_platform_adapter, sample_window_info):
        """Test getting target window when active window exists."""
        mock_platform_adapter.get_app_windows.return_value = sample_window_info
        
        target = app_manager._get_target_window('test_app')
        
        # Should return the active window
        assert target == sample_window_info[0]  # First window is active
    
    def test_get_target_window_non_minimized(self, app_manager, mock_platform_adapter):
        """Test getting target window when no active but non-minimized exists."""
        windows = [
            WindowInfo(
                window_id="1",
                title="Window 1",
                app_name="Test App",
                is_active=False,
                is_minimized=True
            ),
            WindowInfo(
                window_id="2",
                title="Window 2",
                app_name="Test App",
                is_active=False,
                is_minimized=False
            )
        ]
        
        mock_platform_adapter.get_app_windows.return_value = windows
        
        target = app_manager._get_target_window('test_app')
        
        # Should return the non-minimized window
        assert target.window_id == "2"
    
    def test_get_target_window_fallback(self, app_manager, mock_platform_adapter):
        """Test getting target window fallback to first window."""
        windows = [
            WindowInfo(
                window_id="1",
                title="Window 1",
                app_name="Test App",
                is_active=False,
                is_minimized=True
            )
        ]
        
        mock_platform_adapter.get_app_windows.return_value = windows
        
        target = app_manager._get_target_window('test_app')
        
        # Should return the first window as fallback
        assert target.window_id == "1"
    
    def test_get_target_window_no_windows(self, app_manager, mock_platform_adapter):
        """Test getting target window when no windows exist."""
        mock_platform_adapter.get_app_windows.return_value = []
        
        target = app_manager._get_target_window('test_app')
        
        assert target is None
    
    def test_launch_browser_with_url_success(self, app_manager, mock_platform_adapter):
        """Test launching browser with URL successfully."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager._launch_browser_with_url(
            '/Applications/Browser.app',
            'https://example.com',
            ['--arg'],
            False
        )
        
        assert success is True
        mock_platform_adapter.launch_app.assert_called_once()
        
        # Check that URL was added to arguments
        call_args = mock_platform_adapter.launch_app.call_args
        args = call_args[1]['args']
        assert 'https://example.com' in args
    
    def test_launch_browser_with_url_force_new(self, app_manager, mock_platform_adapter):
        """Test launching browser with URL and force new window."""
        mock_platform_adapter.launch_app.return_value = True
        
        success = app_manager._launch_browser_with_url(
            '/Applications/Browser.app',
            'https://example.com',
            [],
            True
        )
        
        assert success is True
        
        # Check that --new-window was added
        call_args = mock_platform_adapter.launch_app.call_args
        args = call_args[1]['args']
        assert '--new-window' in args
        assert 'https://example.com' in args

"""Pytest configuration and fixtures for Terminal Controller tests."""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_config_dir():
    """Create a temporary configuration directory for testing."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test configuration files
    apps_config = {
        'apps': {
            'test_app': {
                'name': 'Test Application',
                'executable': {
                    'macos': '/Applications/TestApp.app',
                    'linux': 'test-app',
                    'windows': 'testapp.exe'
                },
                'type': 'test',
                'description': 'Test application for unit tests',
                'args': ['--test-mode']
            },
            'test_browser': {
                'name': 'Test Browser',
                'executable': {
                    'macos': '/Applications/TestBrowser.app',
                    'linux': 'test-browser',
                    'windows': 'testbrowser.exe'
                },
                'type': 'browser',
                'description': 'Test browser application'
            }
        }
    }
    
    websites_config = {
        'websites': {
            'test_site': {
                'name': 'Test Site',
                'url': 'https://test.example.com',
                'description': 'Test website'
            }
        }
    }
    
    settings_config = {
        'hotkeys': {
            'terminal': 'cmd+shift+t',
            'terminal_linux': 'ctrl+alt+t',
            'terminal_windows': 'ctrl+shift+t'
        },
        'behavior': {
            'auto_focus': True,
            'show_window_selection': True,
            'remember_last_used': True,
            'window_selection_timeout': 10
        },
        'terminal': {
            'default': 'test_terminal',
            'startup_command': '',
            'work_directory': '~'
        },
        'logging': {
            'level': 'INFO',
            'file': 'test.log',
            'max_size': '10MB',
            'backup_count': 3
        },
        'daemon': {
            'pid_file': '/tmp/test_tc.pid',
            'auto_start': False
        }
    }
    
    # Write configuration files
    with open(config_dir / 'apps.yaml', 'w') as f:
        yaml.dump(apps_config, f)
    
    with open(config_dir / 'websites.yaml', 'w') as f:
        yaml.dump(websites_config, f)
    
    with open(config_dir / 'settings.yaml', 'w') as f:
        yaml.dump(settings_config, f)
    
    yield str(config_dir)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_platform_adapter():
    """Create a mock platform adapter for testing."""
    mock_adapter = Mock()
    
    # Set up default return values
    mock_adapter.launch_app.return_value = True
    mock_adapter.get_running_apps.return_value = []
    mock_adapter.get_app_windows.return_value = []
    mock_adapter.activate_window.return_value = True
    mock_adapter.minimize_window.return_value = True
    mock_adapter.close_window.return_value = True
    mock_adapter.register_hotkey.return_value = True
    mock_adapter.unregister_hotkey.return_value = True
    mock_adapter.get_active_window.return_value = None
    mock_adapter.is_app_running.return_value = False
    mock_adapter.kill_app.return_value = True
    mock_adapter.open_url.return_value = True
    mock_adapter.get_default_terminal.return_value = 'test-terminal'
    mock_adapter.normalize_app_path.side_effect = lambda x: x
    
    return mock_adapter


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a ConfigManager instance with test configuration."""
    from src.config_manager import ConfigManager
    return ConfigManager(temp_config_dir)


@pytest.fixture
def command_parser():
    """Create a CommandParser instance for testing."""
    from src.command_parser import CommandParser
    return CommandParser()


@pytest.fixture
def sample_window_info():
    """Create sample WindowInfo objects for testing."""
    from src.platform.base import WindowInfo
    
    return [
        WindowInfo(
            window_id="12345",
            title="Test Window 1",
            app_name="Test App",
            is_active=True,
            is_minimized=False
        ),
        WindowInfo(
            window_id="67890",
            title="Test Window 2",
            app_name="Test App",
            is_active=False,
            is_minimized=True
        )
    ]


@pytest.fixture
def sample_app_info():
    """Create sample AppInfo objects for testing."""
    from src.platform.base import AppInfo, WindowInfo
    
    windows = [
        WindowInfo(
            window_id="12345",
            title="Test Window",
            app_name="Test App",
            is_active=True,
            is_minimized=False
        )
    ]
    
    return AppInfo(
        pid=1234,
        name="Test App",
        executable_path="/path/to/test/app",
        windows=windows
    )


@pytest.fixture(autouse=True)
def mock_platform_detection():
    """Mock platform detection to return a consistent platform for testing."""
    with patch('platform.system') as mock_system:
        mock_system.return_value = 'Darwin'  # Mock as macOS for consistency
        yield mock_system


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for testing."""
    with patch('subprocess.run') as mock_run, \
         patch('subprocess.Popen') as mock_popen:
        
        # Set up default return values
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        mock_popen.return_value.pid = 12345
        mock_popen.return_value.poll.return_value = None
        
        yield {
            'run': mock_run,
            'popen': mock_popen
        }


@pytest.fixture
def mock_file_operations():
    """Mock file system operations for testing."""
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.isfile') as mock_isfile, \
         patch('os.path.isdir') as mock_isdir:
        
        # Set up default return values
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_isdir.return_value = True
        
        yield {
            'exists': mock_exists,
            'isfile': mock_isfile,
            'isdir': mock_isdir
        }

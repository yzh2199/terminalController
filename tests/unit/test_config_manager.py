"""Unit tests for ConfigManager module."""
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config_manager import (
    ConfigManager, AppConfig, WebsiteConfig, SettingsConfig,
    HotkeyConfig, BehaviorConfig, TerminalConfig, LoggingConfig, DaemonConfig
)


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_init_with_config_dir(self, temp_config_dir):
        """Test ConfigManager initialization with custom config directory."""
        config_manager = ConfigManager(temp_config_dir)
        
        assert config_manager.config_dir == Path(temp_config_dir)
        assert config_manager.apps_file == Path(temp_config_dir) / 'apps.yaml'
        assert config_manager.websites_file == Path(temp_config_dir) / 'websites.yaml'
        assert config_manager.settings_file == Path(temp_config_dir) / 'settings.yaml'
    
    def test_init_creates_config_dir(self, tmp_path):
        """Test that ConfigManager creates config directory if it doesn't exist."""
        config_dir = tmp_path / 'new_config'
        config_manager = ConfigManager(str(config_dir))
        
        assert config_dir.exists()
        assert config_dir.is_dir()
    
    def test_load_apps_config(self, config_manager):
        """Test loading application configurations."""
        config_manager._load_apps()
        
        assert 'test_app' in config_manager._apps
        app_config = config_manager._apps['test_app']
        assert app_config.name == 'Test Application'
        assert app_config.type == 'test'
        assert app_config.description == 'Test application for unit tests'
        assert app_config.args == ['--test-mode']
    
    def test_load_websites_config(self, config_manager):
        """Test loading website configurations."""
        config_manager._load_websites()
        
        assert 'test_site' in config_manager._websites
        website_config = config_manager._websites['test_site']
        assert website_config.name == 'Test Site'
        assert website_config.url == 'https://test.example.com'
        assert website_config.description == 'Test website'
    
    def test_load_settings_config(self, config_manager):
        """Test loading settings configuration."""
        config_manager._load_settings()
        
        settings = config_manager._settings
        assert settings.hotkeys.terminal == 'cmd+shift+t'
        assert settings.behavior.auto_focus is True
        assert settings.terminal.default == 'test_terminal'
        assert settings.logging.level == 'INFO'
    
    def test_get_app_config(self, config_manager):
        """Test getting application configuration."""
        app_config = config_manager.get_app_config('test_app')
        
        assert app_config is not None
        assert app_config.name == 'Test Application'
        assert app_config.type == 'test'
    
    def test_get_app_config_not_found(self, config_manager):
        """Test getting application configuration for non-existent app."""
        app_config = config_manager.get_app_config('non_existent')
        assert app_config is None
    
    def test_get_website_config(self, config_manager):
        """Test getting website configuration."""
        website_config = config_manager.get_website_config('test_site')
        
        assert website_config is not None
        assert website_config.name == 'Test Site'
        assert website_config.url == 'https://test.example.com'
    
    def test_get_website_config_not_found(self, config_manager):
        """Test getting website configuration for non-existent website."""
        website_config = config_manager.get_website_config('non_existent')
        assert website_config is None
    
    def test_get_settings(self, config_manager):
        """Test getting settings configuration."""
        settings = config_manager.get_settings()
        
        assert isinstance(settings, SettingsConfig)
        assert settings.hotkeys.terminal == 'cmd+shift+t'
        assert settings.behavior.auto_focus is True
    
    def test_get_all_apps(self, config_manager):
        """Test getting all application configurations."""
        apps = config_manager.get_all_apps()
        
        assert isinstance(apps, dict)
        assert 'test_app' in apps
        assert 'test_browser' in apps
        assert len(apps) == 2
    
    def test_get_all_websites(self, config_manager):
        """Test getting all website configurations."""
        websites = config_manager.get_all_websites()
        
        assert isinstance(websites, dict)
        assert 'test_site' in websites
        assert len(websites) == 1
    
    def test_set_last_used_window(self, config_manager):
        """Test setting last used window."""
        config_manager.set_last_used_window('test_app', 'window_123')
        
        last_used = config_manager.get_last_used_window('test_app')
        assert last_used == 'window_123'
    
    def test_get_last_used_window_not_set(self, config_manager):
        """Test getting last used window when not set."""
        last_used = config_manager.get_last_used_window('test_app')
        assert last_used is None
    
    def test_add_app(self, config_manager):
        """Test adding a new application configuration."""
        new_app = AppConfig(
            name='New App',
            executable={'macos': '/path/to/app'},
            type='editor',
            description='A new app'
        )
        
        success = config_manager.add_app('new_app', new_app)
        assert success is True
        
        retrieved_app = config_manager.get_app_config('new_app')
        assert retrieved_app is not None
        assert retrieved_app.name == 'New App'
    
    def test_remove_app(self, config_manager):
        """Test removing an application configuration."""
        # First ensure the app exists
        assert config_manager.get_app_config('test_app') is not None
        
        success = config_manager.remove_app('test_app')
        assert success is True
        
        # Verify it's removed
        assert config_manager.get_app_config('test_app') is None
    
    def test_remove_app_not_exists(self, config_manager):
        """Test removing a non-existent application."""
        success = config_manager.remove_app('non_existent')
        assert success is True  # Should succeed even if app doesn't exist
    
    def test_add_website(self, config_manager):
        """Test adding a new website configuration."""
        new_website = WebsiteConfig(
            name='New Site',
            url='https://new.example.com',
            description='A new website'
        )
        
        success = config_manager.add_website('new_site', new_website)
        assert success is True
        
        retrieved_website = config_manager.get_website_config('new_site')
        assert retrieved_website is not None
        assert retrieved_website.name == 'New Site'
    
    def test_remove_website(self, config_manager):
        """Test removing a website configuration."""
        # First ensure the website exists
        assert config_manager.get_website_config('test_site') is not None
        
        success = config_manager.remove_website('test_site')
        assert success is True
        
        # Verify it's removed
        assert config_manager.get_website_config('test_site') is None
    
    def test_update_settings(self, config_manager):
        """Test updating settings configuration."""
        new_settings = SettingsConfig()
        new_settings.behavior.auto_focus = False
        new_settings.terminal.default = 'new_terminal'
        
        success = config_manager.update_settings(new_settings)
        assert success is True
        
        updated_settings = config_manager.get_settings()
        assert updated_settings.behavior.auto_focus is False
        assert updated_settings.terminal.default == 'new_terminal'
    
    def test_reload(self, config_manager):
        """Test reloading configuration."""
        # Modify internal state
        config_manager._apps.clear()
        assert len(config_manager._apps) == 0
        
        # Reload should restore from files
        success = config_manager.reload()
        assert success is True
        assert len(config_manager._apps) > 0
    
    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_load_apps_file_not_found(self, mock_open, temp_config_dir):
        """Test loading apps when file doesn't exist."""
        config_manager = ConfigManager(temp_config_dir)
        success = config_manager._load_apps()
        assert success is False
    
    @patch('yaml.safe_load', side_effect=yaml.YAMLError('Invalid YAML'))
    def test_load_apps_invalid_yaml(self, mock_yaml, config_manager):
        """Test loading apps with invalid YAML."""
        success = config_manager._load_apps()
        assert success is False
    
    def test_save_apps(self, config_manager):
        """Test saving applications configuration."""
        config_manager._apps['new_app'] = AppConfig(
            name='New App',
            executable={'macos': '/path/to/app'},
            type='editor'
        )
        
        success = config_manager._save_apps()
        assert success is True
    
    def test_save_websites(self, config_manager):
        """Test saving websites configuration."""
        config_manager._websites['new_site'] = WebsiteConfig(
            name='New Site',
            url='https://new.example.com'
        )
        
        success = config_manager._save_websites()
        assert success is True
    
    def test_save_settings(self, config_manager):
        """Test saving settings configuration."""
        config_manager._settings.behavior.auto_focus = False
        
        success = config_manager._save_settings()
        assert success is True


class TestConfigDataClasses:
    """Test cases for configuration data classes."""
    
    def test_app_config_creation(self):
        """Test AppConfig creation and attributes."""
        app_config = AppConfig(
            name='Test App',
            executable={'macos': '/path/to/app'},
            type='editor',
            description='Test description',
            args=['--test']
        )
        
        assert app_config.name == 'Test App'
        assert app_config.executable == {'macos': '/path/to/app'}
        assert app_config.type == 'editor'
        assert app_config.description == 'Test description'
        assert app_config.args == ['--test']
    
    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        app_config = AppConfig(
            name='Test App',
            executable={'macos': '/path/to/app'},
            type='editor'
        )
        
        assert app_config.description == ''
        assert app_config.args == []
    
    def test_website_config_creation(self):
        """Test WebsiteConfig creation and attributes."""
        website_config = WebsiteConfig(
            name='Test Site',
            url='https://test.com',
            description='Test description'
        )
        
        assert website_config.name == 'Test Site'
        assert website_config.url == 'https://test.com'
        assert website_config.description == 'Test description'
    
    def test_website_config_defaults(self):
        """Test WebsiteConfig default values."""
        website_config = WebsiteConfig(
            name='Test Site',
            url='https://test.com'
        )
        
        assert website_config.description == ''
    
    def test_settings_config_creation(self):
        """Test SettingsConfig creation with nested configs."""
        hotkeys = HotkeyConfig(terminal='cmd+t')
        behavior = BehaviorConfig(auto_focus=False)
        terminal = TerminalConfig(default='test')
        logging_config = LoggingConfig(level='DEBUG')
        daemon = DaemonConfig(auto_start=True)
        
        settings = SettingsConfig(
            hotkeys=hotkeys,
            behavior=behavior,
            terminal=terminal,
            logging=logging_config,
            daemon=daemon
        )
        
        assert settings.hotkeys.terminal == 'cmd+t'
        assert settings.behavior.auto_focus is False
        assert settings.terminal.default == 'test'
        assert settings.logging.level == 'DEBUG'
        assert settings.daemon.auto_start is True
    
    def test_settings_config_defaults(self):
        """Test SettingsConfig default values."""
        settings = SettingsConfig()
        
        assert isinstance(settings.hotkeys, HotkeyConfig)
        assert isinstance(settings.behavior, BehaviorConfig)
        assert isinstance(settings.terminal, TerminalConfig)
        assert isinstance(settings.logging, LoggingConfig)
        assert isinstance(settings.daemon, DaemonConfig)
        
        # Test some default values
        assert settings.hotkeys.terminal == 'cmd+shift+t'
        assert settings.behavior.auto_focus is True
        assert settings.terminal.default == 't'
        assert settings.logging.level == 'INFO'
        assert settings.daemon.auto_start is False

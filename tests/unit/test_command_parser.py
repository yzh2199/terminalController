"""Unit tests for CommandParser module."""
import pytest

from src.command_parser import CommandParser, CommandType, ParsedCommand


class TestCommandParser:
    """Test cases for CommandParser class."""
    
    def test_init(self):
        """Test CommandParser initialization."""
        parser = CommandParser()
        
        assert parser._window_actions == {
            'activate', 'focus', 'show',
            'minimize', 'min', 'hide',
            'close', 'kill',
            'list', 'ls'
        }
        assert parser._help_commands == {
            'help', 'h', '?', '--help', '-h'
        }
    
    def test_parse_empty_command(self, command_parser):
        """Test parsing empty or whitespace command."""
        assert command_parser.parse("") is None
        assert command_parser.parse("   ") is None
        assert command_parser.parse(None) is None
    
    def test_parse_simple_app_launch(self, command_parser):
        """Test parsing simple application launch command."""
        parsed = command_parser.parse("chrome")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.LAUNCH_APP
        assert parsed.app_id == "chrome"
        assert parsed.website_id is None
        assert parsed.url is None
        assert parsed.raw_command == "chrome"
    
    def test_parse_app_with_website(self, command_parser):
        """Test parsing application launch with website."""
        parsed = command_parser.parse("chrome google")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.OPEN_URL
        assert parsed.app_id == "chrome"
        assert parsed.website_id == "google"
        assert parsed.url is None
    
    def test_parse_app_with_url(self, command_parser):
        """Test parsing application launch with direct URL."""
        parsed = command_parser.parse("chrome https://github.com")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.OPEN_URL
        assert parsed.app_id == "chrome"
        assert parsed.website_id is None
        assert parsed.url == "https://github.com"
    
    def test_parse_app_with_options(self, command_parser):
        """Test parsing application launch with options."""
        parsed = command_parser.parse("chrome --new")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.LAUNCH_APP
        assert parsed.app_id == "chrome"
        assert parsed.options.get("new") is True
    
    def test_parse_app_with_options_and_values(self, command_parser):
        """Test parsing application with options that have values."""
        parsed = command_parser.parse("chrome --profile default google")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.OPEN_URL
        assert parsed.app_id == "chrome"
        assert parsed.website_id == "google"
        assert parsed.options.get("profile") == "default"
    
    def test_parse_help_command(self, command_parser):
        """Test parsing help command."""
        parsed = command_parser.parse("help")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.HELP
        assert parsed.options.get("topic") is None
    
    def test_parse_help_with_topic(self, command_parser):
        """Test parsing help command with topic."""
        parsed = command_parser.parse("help commands")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.HELP
        assert parsed.options.get("topic") == "commands"
    
    def test_parse_config_command(self, command_parser):
        """Test parsing config command."""
        parsed = command_parser.parse("config")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.CONFIG
        assert parsed.options.get("action") == "show"
    
    def test_parse_config_with_action(self, command_parser):
        """Test parsing config command with action."""
        parsed = command_parser.parse("config reload")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.CONFIG
        assert parsed.options.get("action") == "reload"
    
    def test_parse_config_list_apps(self, command_parser):
        """Test parsing config list apps command."""
        parsed = command_parser.parse("config list apps")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.CONFIG
        assert parsed.options.get("action") == "list"
        assert parsed.options.get("args") == ["apps"]
    
    def test_parse_quit_command(self, command_parser):
        """Test parsing quit command."""
        parsed = command_parser.parse("quit")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.QUIT
        assert parsed.options.get("force") is False
    
    def test_parse_quit_with_force(self, command_parser):
        """Test parsing quit command with force option."""
        parsed = command_parser.parse("quit --force")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.QUIT
        assert parsed.options.get("force") is True
    
    def test_parse_window_list(self, command_parser):
        """Test parsing window list command."""
        parsed = command_parser.parse("chrome list")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.WINDOW_CONTROL
        assert parsed.app_id == "chrome"
        assert parsed.window_action == "list"
    
    def test_parse_window_activate(self, command_parser):
        """Test parsing window activate command."""
        parsed = command_parser.parse("chrome activate 12345")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.WINDOW_CONTROL
        assert parsed.app_id == "chrome"
        assert parsed.window_action == "activate"
        assert parsed.window_id == "12345"
    
    def test_parse_window_minimize(self, command_parser):
        """Test parsing window minimize command."""
        parsed = command_parser.parse("chrome minimize")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.WINDOW_CONTROL
        assert parsed.app_id == "chrome"
        assert parsed.window_action == "minimize"
        assert parsed.window_id is None
    
    def test_parse_window_close_with_id(self, command_parser):
        """Test parsing window close command with window ID."""
        parsed = command_parser.parse("close 12345")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.WINDOW_CONTROL
        assert parsed.app_id is None
        assert parsed.window_action == "close"
        assert parsed.window_id == "12345"
    
    def test_parse_direct_window_action(self, command_parser):
        """Test parsing direct window action without app."""
        parsed = command_parser.parse("activate 12345")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.WINDOW_CONTROL
        assert parsed.app_id is None
        assert parsed.window_action == "activate"
        assert parsed.window_id == "12345"
    
    def test_parse_window_action_aliases(self, command_parser):
        """Test parsing window action aliases."""
        # Test focus -> activate
        parsed = command_parser.parse("chrome focus")
        assert parsed.window_action == "activate"
        
        # Test min -> minimize
        parsed = command_parser.parse("chrome min")
        assert parsed.window_action == "minimize"
        
        # Test kill -> close
        parsed = command_parser.parse("chrome kill")
        assert parsed.window_action == "close"
        
        # Test ls -> list
        parsed = command_parser.parse("chrome ls")
        assert parsed.window_action == "list"
    
    def test_parse_quoted_arguments(self, command_parser):
        """Test parsing commands with quoted arguments."""
        parsed = command_parser.parse('chrome "https://example.com/path with spaces"')
        
        assert parsed is not None
        assert parsed.command_type == CommandType.OPEN_URL
        assert parsed.url == "https://example.com/path with spaces"
    
    def test_parse_complex_command(self, command_parser):
        """Test parsing complex command with multiple options."""
        parsed = command_parser.parse("chrome --new --profile work https://github.com")
        
        assert parsed is not None
        assert parsed.command_type == CommandType.OPEN_URL
        assert parsed.app_id == "chrome"
        assert parsed.url == "https://github.com"
        assert parsed.options.get("new") is True
        assert parsed.options.get("profile") == "work"
    
    def test_is_url_valid_http(self, command_parser):
        """Test URL detection for HTTP URLs."""
        assert command_parser._is_url("http://example.com") is True
        assert command_parser._is_url("https://example.com") is True
        assert command_parser._is_url("https://github.com/user/repo") is True
        assert command_parser._is_url("http://localhost:8080") is True
    
    def test_is_url_invalid(self, command_parser):
        """Test URL detection for invalid URLs."""
        assert command_parser._is_url("not-a-url") is False
        assert command_parser._is_url("example.com") is False
        assert command_parser._is_url("ftp://example.com") is False
        assert command_parser._is_url("") is False
    
    def test_validate_command_valid_app(self, command_parser):
        """Test command validation with valid application."""
        parsed = ParsedCommand(
            command_type=CommandType.LAUNCH_APP,
            app_id="chrome"
        )
        
        available_apps = ["chrome", "firefox"]
        available_websites = ["google", "github"]
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is True
        assert error is None
    
    def test_validate_command_invalid_app(self, command_parser):
        """Test command validation with invalid application."""
        parsed = ParsedCommand(
            command_type=CommandType.LAUNCH_APP,
            app_id="unknown"
        )
        
        available_apps = ["chrome", "firefox"]
        available_websites = ["google", "github"]
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is False
        assert "Unknown application: unknown" in error
    
    def test_validate_command_valid_website(self, command_parser):
        """Test command validation with valid website."""
        parsed = ParsedCommand(
            command_type=CommandType.OPEN_URL,
            app_id="chrome",
            website_id="google"
        )
        
        available_apps = ["chrome", "firefox"]
        available_websites = ["google", "github"]
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is True
        assert error is None
    
    def test_validate_command_invalid_website(self, command_parser):
        """Test command validation with invalid website."""
        parsed = ParsedCommand(
            command_type=CommandType.OPEN_URL,
            app_id="chrome",
            website_id="unknown"
        )
        
        available_apps = ["chrome", "firefox"]
        available_websites = ["google", "github"]
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is False
        assert "Unknown website: unknown" in error
    
    def test_validate_window_control_valid(self, command_parser):
        """Test validation of valid window control command."""
        parsed = ParsedCommand(
            command_type=CommandType.WINDOW_CONTROL,
            app_id="chrome",
            window_action="activate"
        )
        
        available_apps = ["chrome"]
        available_websites = []
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is True
        assert error is None
    
    def test_validate_window_control_invalid_action(self, command_parser):
        """Test validation of window control with invalid action."""
        parsed = ParsedCommand(
            command_type=CommandType.WINDOW_CONTROL,
            app_id="chrome",
            window_action="invalid"
        )
        
        available_apps = ["chrome"]
        available_websites = []
        
        is_valid, error = command_parser.validate_command(
            parsed, available_apps, available_websites
        )
        
        assert is_valid is False
        assert "Invalid window action: invalid" in error
    
    def test_get_help_text_general(self, command_parser):
        """Test getting general help text."""
        help_text = command_parser.get_help_text()
        
        assert "Terminal Controller Commands:" in help_text
        assert "Application Launch:" in help_text
        assert "Window Control:" in help_text
        assert "Configuration:" in help_text
    
    def test_get_help_text_apps(self, command_parser):
        """Test getting help text for applications."""
        help_text = command_parser.get_help_text("apps")
        
        assert "Available Applications:" in help_text
        assert "Chrome" in help_text
        assert "Cursor" in help_text
    
    def test_get_help_text_websites(self, command_parser):
        """Test getting help text for websites."""
        help_text = command_parser.get_help_text("websites")
        
        assert "Available Websites:" in help_text
        assert "Google" in help_text
        assert "GitHub" in help_text
    
    def test_get_help_text_unknown_topic(self, command_parser):
        """Test getting help text for unknown topic."""
        help_text = command_parser.get_help_text("unknown")
        
        assert "Unknown help topic: unknown" in help_text
        assert "Available topics:" in help_text


class TestParsedCommand:
    """Test cases for ParsedCommand class."""
    
    def test_parsed_command_creation(self):
        """Test ParsedCommand creation with all parameters."""
        parsed = ParsedCommand(
            command_type=CommandType.LAUNCH_APP,
            app_id="chrome",
            website_id="google",
            url="https://example.com",
            window_action="activate",
            window_id="12345",
            options={"new": True},
            raw_command="chrome --new google"
        )
        
        assert parsed.command_type == CommandType.LAUNCH_APP
        assert parsed.app_id == "chrome"
        assert parsed.website_id == "google"
        assert parsed.url == "https://example.com"
        assert parsed.window_action == "activate"
        assert parsed.window_id == "12345"
        assert parsed.options == {"new": True}
        assert parsed.raw_command == "chrome --new google"
    
    def test_parsed_command_defaults(self):
        """Test ParsedCommand default values."""
        parsed = ParsedCommand(command_type=CommandType.HELP)
        
        assert parsed.command_type == CommandType.HELP
        assert parsed.app_id is None
        assert parsed.website_id is None
        assert parsed.url is None
        assert parsed.window_action is None
        assert parsed.window_id is None
        assert parsed.options == {}
        assert parsed.raw_command == ""
    
    def test_parsed_command_post_init(self):
        """Test ParsedCommand __post_init__ method."""
        # Test with None options
        parsed = ParsedCommand(
            command_type=CommandType.HELP,
            options=None
        )
        
        assert parsed.options == {}


class TestCommandType:
    """Test cases for CommandType enum."""
    
    def test_command_type_values(self):
        """Test CommandType enum values."""
        assert CommandType.LAUNCH_APP.value == "launch_app"
        assert CommandType.OPEN_URL.value == "open_url"
        assert CommandType.WINDOW_CONTROL.value == "window_control"
        assert CommandType.HELP.value == "help"
        assert CommandType.CONFIG.value == "config"
        assert CommandType.QUIT.value == "quit"

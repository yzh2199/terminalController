"""Command parsing module for Terminal Controller."""
import re
import shlex
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Types of commands that can be parsed."""
    LAUNCH_APP = "launch_app"
    OPEN_URL = "open_url"
    WINDOW_CONTROL = "window_control"
    HELP = "help"
    CONFIG = "config"
    QUIT = "quit"


@dataclass
class ParsedCommand:
    """Represents a parsed command."""
    command_type: CommandType
    app_id: Optional[str] = None
    website_id: Optional[str] = None
    url: Optional[str] = None
    window_action: Optional[str] = None
    window_id: Optional[str] = None
    options: Dict[str, Any] = None
    raw_command: str = ""
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


class CommandParser:
    """Parses user input commands into structured command objects."""
    
    def __init__(self):
        """Initialize the command parser."""
        self._window_actions = {
            'activate', 'focus', 'show',
            'minimize', 'min', 'hide',
            'close', 'kill',
            'list', 'ls'
        }
        
        self._help_commands = {
            'help', 'h', '?', '--help', '-h'
        }
        
        self._config_commands = {
            'config', 'cfg', 'settings', 'set'
        }
        
        self._quit_commands = {
            'quit', 'exit', 'q'
        }
    
    def parse(self, command: str) -> Optional[ParsedCommand]:
        """Parse a command string into a structured command object.
        
        Args:
            command: Raw command string from user input
            
        Returns:
            ParsedCommand object or None if parsing failed
        """
        if not command or not command.strip():
            return None
        
        command = command.strip()
        
        try:
            # Try to parse as shell-like command with proper quoting
            try:
                tokens = shlex.split(command)
            except ValueError:
                # Fallback to simple split if shlex fails
                tokens = command.split()
            
            if not tokens:
                return None
            
            # Check for special commands first
            if tokens[0].lower() in self._help_commands:
                return self._parse_help_command(tokens, command)
            
            if tokens[0].lower() in self._config_commands:
                return self._parse_config_command(tokens, command)
            
            if tokens[0].lower() in self._quit_commands:
                return self._parse_quit_command(tokens, command)
            
            # Check for window control commands
            if len(tokens) >= 2 and tokens[1].lower() in self._window_actions:
                return self._parse_window_command(tokens, command)
            
            # Check for direct window actions
            if tokens[0].lower() in self._window_actions:
                return self._parse_window_command(tokens, command)
            
            # Parse as app/website command
            return self._parse_app_command(tokens, command)
            
        except Exception as e:
            logger.error(f"Failed to parse command '{command}': {e}")
            return None
    
    def _parse_app_command(self, tokens: List[str], raw_command: str) -> Optional[ParsedCommand]:
        """Parse an application launch command.
        
        Args:
            tokens: Tokenized command
            raw_command: Original command string
            
        Returns:
            ParsedCommand for app launch or URL opening
        """
        app_id = tokens[0]
        options = {}
        website_id = None
        url = None
        
        # Parse additional arguments
        i = 1
        while i < len(tokens):
            token = tokens[i]
            
            # Check for options
            if token.startswith('--'):
                option_name = token[2:]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith('-'):
                    # Option with value
                    options[option_name] = tokens[i + 1]
                    i += 2
                else:
                    # Boolean option
                    options[option_name] = True
                    i += 1
            elif token.startswith('-'):
                # Short options
                option_name = token[1:]
                if i + 1 < len(tokens) and not tokens[i + 1].startswith('-'):
                    options[option_name] = tokens[i + 1]
                    i += 2
                else:
                    options[option_name] = True
                    i += 1
            else:
                # Could be website ID or URL
                if self._is_url(token):
                    url = token
                else:
                    website_id = token
                i += 1
        
        # Determine command type
        if url:
            return ParsedCommand(
                command_type=CommandType.OPEN_URL,
                app_id=app_id,
                url=url,
                options=options,
                raw_command=raw_command
            )
        elif website_id:
            return ParsedCommand(
                command_type=CommandType.OPEN_URL,
                app_id=app_id,
                website_id=website_id,
                options=options,
                raw_command=raw_command
            )
        else:
            return ParsedCommand(
                command_type=CommandType.LAUNCH_APP,
                app_id=app_id,
                options=options,
                raw_command=raw_command
            )
    
    def _parse_window_command(self, tokens: List[str], raw_command: str) -> Optional[ParsedCommand]:
        """Parse a window control command.
        
        Args:
            tokens: Tokenized command
            raw_command: Original command string
            
        Returns:
            ParsedCommand for window control
        """
        if len(tokens) < 2:
            return None
        
        if tokens[0].lower() in self._window_actions:
            # Direct window action: "minimize 12345"
            action = tokens[0].lower()
            target = tokens[1] if len(tokens) > 1 else None
        else:
            # App with action: "chrome minimize" or "chrome minimize 12345"
            app_id = tokens[0]
            action = tokens[1].lower()
            target = tokens[2] if len(tokens) > 2 else None
        
        # Normalize action names
        action_mapping = {
            'focus': 'activate',
            'show': 'activate',
            'min': 'minimize',
            'hide': 'minimize',
            'kill': 'close',
            'ls': 'list'
        }
        
        normalized_action = action_mapping.get(action, action)
        
        return ParsedCommand(
            command_type=CommandType.WINDOW_CONTROL,
            app_id=app_id if tokens[0].lower() not in self._window_actions else None,
            window_action=normalized_action,
            window_id=target if target and target.isdigit() else None,
            options={'target': target} if target and not target.isdigit() else {},
            raw_command=raw_command
        )
    
    def _parse_help_command(self, tokens: List[str], raw_command: str) -> ParsedCommand:
        """Parse a help command.
        
        Args:
            tokens: Tokenized command
            raw_command: Original command string
            
        Returns:
            ParsedCommand for help
        """
        topic = tokens[1] if len(tokens) > 1 else None
        return ParsedCommand(
            command_type=CommandType.HELP,
            options={'topic': topic},
            raw_command=raw_command
        )
    
    def _parse_config_command(self, tokens: List[str], raw_command: str) -> ParsedCommand:
        """Parse a configuration command.
        
        Args:
            tokens: Tokenized command
            raw_command: Original command string
            
        Returns:
            ParsedCommand for configuration
        """
        action = tokens[1] if len(tokens) > 1 else 'show'
        options = {'action': action}
        
        if len(tokens) > 2:
            options['args'] = tokens[2:]
        
        return ParsedCommand(
            command_type=CommandType.CONFIG,
            options=options,
            raw_command=raw_command
        )
    
    def _parse_quit_command(self, tokens: List[str], raw_command: str) -> ParsedCommand:
        """Parse a quit command.
        
        Args:
            tokens: Tokenized command
            raw_command: Original command string
            
        Returns:
            ParsedCommand for quit
        """
        force = '--force' in tokens or '-f' in tokens
        return ParsedCommand(
            command_type=CommandType.QUIT,
            options={'force': force},
            raw_command=raw_command
        )
    
    def _is_url(self, text: str) -> bool:
        """Check if a string is a URL.
        
        Args:
            text: String to check
            
        Returns:
            True if the string appears to be a URL
        """
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(text))
    
    def get_help_text(self, topic: Optional[str] = None) -> str:
        """Get help text for commands.
        
        Args:
            topic: Specific topic to get help for
            
        Returns:
            Help text string
        """
        if topic == "commands" or topic is None:
            return """Terminal Controller Commands:

Application Launch:
  <app_id>                    Launch application
  <app_id> <website_id>       Launch app and open website
  <app_id> <url>              Launch app and open URL
  <app_id> --new              Force new window/instance

Window Control:
  <app_id> list               List windows for application
  <app_id> activate [id]      Activate window (latest if no ID)
  <app_id> minimize [id]      Minimize window
  <app_id> close [id]         Close window
  
  activate <window_id>        Activate specific window
  minimize <window_id>        Minimize specific window
  close <window_id>           Close specific window
  list                        List all windows

Configuration:
  config                      Show current configuration
  config reload               Reload configuration files
  config list apps            List available applications
  config list websites        List available websites

Other:
  help [topic]                Show help (topics: commands, apps, websites)
  quit                        Exit Terminal Controller

Examples:
  c                          Open Chrome
  c g                        Open Chrome with Google
  c https://github.com       Open Chrome with GitHub
  cur --new                  Open new Cursor window
  chrome list                List Chrome windows
  chrome activate 12345      Activate Chrome window 12345
"""
        
        elif topic == "apps":
            return """Available Applications:
  c    - Google Chrome
  cur  - Cursor Editor
  t    - Terminal (iTerm)
  p    - Postman
  vs   - Visual Studio Code

Use 'config list apps' for detailed information.
"""
        
        elif topic == "websites":
            return """Available Websites:
  g    - Google (https://www.google.com)
  gh   - GitHub (https://github.com)
  gpt  - ChatGPT (https://chat.openai.com)
  yt   - YouTube (https://www.youtube.com)
  tw   - Twitter (https://twitter.com)
  l    - LinkedIn (https://www.linkedin.com)
  r    - Reddit (https://www.reddit.com)

Use 'config list websites' for detailed information.
"""
        
        else:
            return f"Unknown help topic: {topic}. Available topics: commands, apps, websites"
    
    def validate_command(self, parsed_cmd: ParsedCommand, available_apps: List[str], 
                        available_websites: List[str]) -> Tuple[bool, Optional[str]]:
        """Validate a parsed command against available configurations.
        
        Args:
            parsed_cmd: Parsed command to validate
            available_apps: List of available application IDs
            available_websites: List of available website IDs
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if parsed_cmd.command_type == CommandType.LAUNCH_APP:
            if parsed_cmd.app_id and parsed_cmd.app_id not in available_apps:
                return False, f"Unknown application: {parsed_cmd.app_id}"
        
        elif parsed_cmd.command_type == CommandType.OPEN_URL:
            if parsed_cmd.app_id and parsed_cmd.app_id not in available_apps:
                return False, f"Unknown application: {parsed_cmd.app_id}"
            
            if parsed_cmd.website_id and parsed_cmd.website_id not in available_websites:
                return False, f"Unknown website: {parsed_cmd.website_id}"
        
        elif parsed_cmd.command_type == CommandType.WINDOW_CONTROL:
            if parsed_cmd.app_id and parsed_cmd.app_id not in available_apps:
                return False, f"Unknown application: {parsed_cmd.app_id}"
            
            valid_actions = {'activate', 'minimize', 'close', 'list'}
            if parsed_cmd.window_action not in valid_actions:
                return False, f"Invalid window action: {parsed_cmd.window_action}"
        
        return True, None

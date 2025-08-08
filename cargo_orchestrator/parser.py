import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MessageLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"
    HELP = "help"
    INFO = "info"


@dataclass
class CodeSpan:
    """Represents a span of code in a file."""
    file_name: str
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    text: Optional[str] = None


@dataclass
class BuildMessage:
    """Represents a single error, warning, or other message from cargo build."""
    level: MessageLevel
    message: str
    code: Optional[str] = None
    spans: List[CodeSpan] = None
    children: List['BuildMessage'] = None
    rendered: Optional[str] = None
    
    def __post_init__(self):
        if self.spans is None:
            self.spans = []
        if self.children is None:
            self.children = []


class CargoOutputParser:
    """Parser for cargo build output in both JSON and human-readable formats."""
    
    def parse_json_output(self, output: str) -> List[BuildMessage]:
        """
        Parse JSON-formatted cargo output.
        
        Args:
            output: The stdout from cargo build with --message-format json
            
        Returns:
            List of BuildMessage objects
        """
        messages = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
                
            try:
                data = json.loads(line)
                
                # We're only interested in compiler messages
                if data.get('reason') != 'compiler-message':
                    continue
                
                message_data = data.get('message', {})
                message = self._parse_json_message(message_data)
                if message:
                    messages.append(message)
                    
            except json.JSONDecodeError:
                # Skip lines that aren't valid JSON
                continue
        
        return messages
    
    def _parse_json_message(self, data: Dict[str, Any]) -> Optional[BuildMessage]:
        """Parse a single JSON message object."""
        level_str = data.get('level', '').lower()
        
        # Map cargo levels to our MessageLevel enum
        level_map = {
            'error': MessageLevel.ERROR,
            'warning': MessageLevel.WARNING,
            'note': MessageLevel.NOTE,
            'help': MessageLevel.HELP,
            'info': MessageLevel.INFO,
        }
        
        level = level_map.get(level_str)
        if not level:
            return None
        
        # Parse spans
        spans = []
        for span_data in data.get('spans', []):
            span = self._parse_span(span_data)
            if span:
                spans.append(span)
        
        # Parse children recursively
        children = []
        for child_data in data.get('children', []):
            child = self._parse_json_message(child_data)
            if child:
                children.append(child)
        
        return BuildMessage(
            level=level,
            message=data.get('message', ''),
            code=data.get('code', {}).get('code') if data.get('code') else None,
            spans=spans,
            children=children,
            rendered=data.get('rendered'),
        )
    
    def _parse_span(self, span_data: Dict[str, Any]) -> Optional[CodeSpan]:
        """Parse a span object from JSON."""
        file_name = span_data.get('file_name')
        if not file_name:
            return None
        
        return CodeSpan(
            file_name=file_name,
            line_start=span_data.get('line_start', 0),
            line_end=span_data.get('line_end', 0),
            column_start=span_data.get('column_start', 0),
            column_end=span_data.get('column_end', 0),
            text=span_data.get('text', [{}])[0].get('text') if span_data.get('text') else None,
        )
    
    def parse_human_output(self, output: str) -> List[BuildMessage]:
        """
        Parse human-readable cargo output.
        
        This is a best-effort parser that extracts errors and warnings
        from the standard cargo output format.
        
        Args:
            output: The stderr from cargo build
            
        Returns:
            List of BuildMessage objects
        """
        messages = []
        
        # Regex patterns for parsing cargo output
        # Example: "error[E0425]: cannot find value `x` in this scope"
        message_pattern = re.compile(
            r'^(error|warning|note|help)(?:\[([A-Z0-9]+)\])?: (.+)$',
            re.MULTILINE
        )
        
        # Example: " --> src/main.rs:10:5"
        location_pattern = re.compile(
            r'^\s*--> ([^:]+):(\d+):(\d+)$',
            re.MULTILINE
        )
        
        # Split output into sections by error/warning messages
        current_message = None
        current_text = []
        
        for line in output.split('\n'):
            # Check if this is a new error/warning
            match = message_pattern.match(line)
            if match:
                # Save previous message if exists
                if current_message:
                    current_message.rendered = '\n'.join(current_text)
                    messages.append(current_message)
                
                # Start new message
                level_str = match.group(1)
                code = match.group(2)
                message = match.group(3)
                
                level_map = {
                    'error': MessageLevel.ERROR,
                    'warning': MessageLevel.WARNING,
                    'note': MessageLevel.NOTE,
                    'help': MessageLevel.HELP,
                }
                
                current_message = BuildMessage(
                    level=level_map.get(level_str, MessageLevel.INFO),
                    message=message,
                    code=code,
                )
                current_text = [line]
            
            elif current_message:
                current_text.append(line)
                
                # Check for location information
                loc_match = location_pattern.match(line)
                if loc_match:
                    file_name = loc_match.group(1)
                    line_num = int(loc_match.group(2))
                    col_num = int(loc_match.group(3))
                    
                    span = CodeSpan(
                        file_name=file_name,
                        line_start=line_num,
                        line_end=line_num,
                        column_start=col_num,
                        column_end=col_num,
                    )
                    current_message.spans.append(span)
        
        # Don't forget the last message
        if current_message:
            current_message.rendered = '\n'.join(current_text)
            messages.append(current_message)
        
        return messages
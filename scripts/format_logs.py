#!/usr/bin/env python3
"""Format Databricks App logs with colors and better readability."""

import json
import re
import sys
from datetime import datetime
from typing import Any, Dict


# ANSI color codes
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_YELLOW = '\033[43m'
    BG_GREEN = '\033[42m'


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return f"{Colors.DIM}{dt.strftime('%H:%M:%S')}{Colors.RESET}"
    except Exception:
        return f"{Colors.DIM}{timestamp_str}{Colors.RESET}"


def get_level_color(level: str) -> str:
    """Get color for log level."""
    level = level.upper()
    if level == 'ERROR':
        return f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}"
    elif level == 'WARNING' or level == 'WARN':
        return f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}"
    elif level == 'INFO':
        return f"{Colors.BRIGHT_CYAN}"
    elif level == 'DEBUG':
        return f"{Colors.DIM}"
    else:
        return Colors.WHITE


def format_json_log(log_dict: Dict[str, Any]) -> str:
    """Format a JSON log entry with colors."""
    parts = []
    
    # Timestamp
    if 'timestamp' in log_dict:
        parts.append(format_timestamp(log_dict['timestamp']))
    
    # Level
    if 'level' in log_dict:
        level = log_dict['level']
        color = get_level_color(level)
        parts.append(f"{color}{level:7s}{Colors.RESET}")
    
    # Message
    if 'message' in log_dict:
        message = log_dict['message']
        
        # Highlight HTTP methods and status codes
        message = re.sub(r'\b(GET|POST|PUT|DELETE|PATCH|OPTIONS)\b', 
                        f'{Colors.BOLD}{Colors.BRIGHT_MAGENTA}\\1{Colors.RESET}', 
                        message)
        message = re.sub(r'\b(2\d{2})\b', 
                        f'{Colors.BRIGHT_GREEN}\\1{Colors.RESET}', 
                        message)
        message = re.sub(r'\b(4\d{2})\b', 
                        f'{Colors.BRIGHT_YELLOW}\\1{Colors.RESET}', 
                        message)
        message = re.sub(r'\b(5\d{2})\b', 
                        f'{Colors.BRIGHT_RED}\\1{Colors.RESET}', 
                        message)
        
        parts.append(message)
    
    # Event type
    if 'event' in log_dict and 'message' not in log_dict:
        event = log_dict['event']
        parts.append(f"{Colors.BRIGHT_BLUE}[{event}]{Colors.RESET}")
    
    # Build main line
    main_line = ' │ '.join(parts)
    
    # Additional context (skip common fields)
    skip_fields = {'timestamp', 'level', 'message', 'module', 'function', 'event'}
    context = []
    
    # Prioritize important fields
    important_fields = ['request_id', 'user_id', 'endpoint', 'method', 'status_code', 'duration_ms']
    for field in important_fields:
        if field in log_dict and field not in skip_fields:
            value = log_dict[field]
            if field == 'duration_ms':
                # Color code duration
                duration = float(value)
                if duration < 100:
                    color = Colors.BRIGHT_GREEN
                elif duration < 1000:
                    color = Colors.BRIGHT_YELLOW
                else:
                    color = Colors.BRIGHT_RED
                context.append(f"{Colors.DIM}{field}:{Colors.RESET} {color}{value}ms{Colors.RESET}")
            elif field == 'status_code':
                status = int(value)
                if 200 <= status < 300:
                    color = Colors.BRIGHT_GREEN
                elif 400 <= status < 500:
                    color = Colors.BRIGHT_YELLOW
                else:
                    color = Colors.BRIGHT_RED
                context.append(f"{Colors.DIM}{field}:{Colors.RESET} {color}{value}{Colors.RESET}")
            else:
                context.append(f"{Colors.DIM}{field}:{Colors.RESET} {Colors.BRIGHT_WHITE}{value}{Colors.RESET}")
    
    # Add remaining fields
    for key, value in log_dict.items():
        if key not in skip_fields and key not in important_fields:
            # Don't show super long values
            str_value = str(value)
            if len(str_value) > 100:
                str_value = str_value[:97] + '...'
            context.append(f"{Colors.DIM}{key}:{Colors.RESET} {str_value}")
    
    # Build final output
    result = main_line
    if context:
        result += f"\n  {Colors.DIM}↳{Colors.RESET} " + f" {Colors.DIM}•{Colors.RESET} ".join(context)
    
    return result


def format_uvicorn_log(line: str) -> str:
    """Format uvicorn HTTP access logs."""
    # Match: INFO:     127.0.0.1:52133 - "GET /api/user/me HTTP/1.1" 200 OK
    match = re.match(r'^(INFO|WARNING|ERROR):\s+(.+?)\s+-\s+"(\w+)\s+(.+?)\s+HTTP/[\d.]+"?\s+(\d+)\s+(.+)$', line)
    if match:
        level, client, method, path, status, status_text = match.groups()
        
        # Color the method
        method_colored = f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}{method}{Colors.RESET}"
        
        # Color the status
        status_int = int(status)
        if 200 <= status_int < 300:
            status_colored = f"{Colors.BRIGHT_GREEN}{status} {status_text}{Colors.RESET}"
        elif 400 <= status_int < 500:
            status_colored = f"{Colors.BRIGHT_YELLOW}{status} {status_text}{Colors.RESET}"
        else:
            status_colored = f"{Colors.BRIGHT_RED}{status} {status_text}{Colors.RESET}"
        
        return f"{Colors.DIM}{client}{Colors.RESET} {method_colored} {Colors.BRIGHT_BLUE}{path}{Colors.RESET} → {status_colored}"
    
    return line


def format_vite_log(line: str) -> str:
    """Format Vite frontend server logs."""
    # Highlight URLs
    line = re.sub(r'(https?://[^\s]+)', 
                 f'{Colors.BRIGHT_CYAN}\\1{Colors.RESET}', 
                 line)
    
    # Highlight "ready" messages
    if 'ready' in line.lower():
        line = re.sub(r'(ready)', 
                     f'{Colors.BRIGHT_GREEN}\\1{Colors.RESET}', 
                     line, flags=re.IGNORECASE)
    
    return line


def format_startup_log(line: str) -> str:
    """Format startup messages with emojis."""
    # Already has color/emojis, just make sure they stand out
    if line.startswith('✅') or line.startswith('🚀'):
        return f"{Colors.BRIGHT_GREEN}{line}{Colors.RESET}"
    elif line.startswith('⚠️'):
        return f"{Colors.BRIGHT_YELLOW}{line}{Colors.RESET}"
    elif line.startswith('🔐') or line.startswith('🔧'):
        return f"{Colors.BRIGHT_CYAN}{line}{Colors.RESET}"
    
    return line


def format_warning_log(line: str) -> str:
    """Format Python warning logs."""
    if line.startswith('WARNING:'):
        parts = line.split(':', 2)
        if len(parts) >= 3:
            module = parts[1]
            message = parts[2]
            return f"{Colors.BRIGHT_YELLOW}WARNING{Colors.RESET} {Colors.DIM}[{module}]{Colors.RESET} {message}"
    
    return line


def format_log_line(line: str) -> str:
    """Format a single log line with colors."""
    line = line.rstrip()
    
    if not line:
        return ''
    
    # Try to parse as JSON first
    if line.startswith('{'):
        try:
            log_dict = json.loads(line)
            return format_json_log(log_dict)
        except json.JSONDecodeError:
            pass
    
    # Check for different log formats
    if line.startswith('INFO:     ') and ' - "' in line:
        return format_uvicorn_log(line)
    elif line.startswith('WARNING:'):
        return format_warning_log(line)
    elif any(emoji in line for emoji in ['✅', '🚀', '⚠️', '🔐', '🔧', '🌐', '🖥️', '🔄', '📊', '🛑']):
        return format_startup_log(line)
    elif 'VITE' in line or '➜  Local:' in line:
        return format_vite_log(line)
    
    # Default: return as-is (might be continuation or unknown format)
    return f"{Colors.DIM}{line}{Colors.RESET}"


def main():
    """Main entry point - read from stdin and format output."""
    # Ensure stdout is unbuffered
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        for line in sys.stdin:
            formatted = format_log_line(line)
            if formatted:
                print(formatted, flush=True)
                sys.stdout.flush()  # Extra flush for good measure
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        # Handle graceful shutdown when pipe is closed
        sys.stderr.close()


if __name__ == '__main__':
    main()


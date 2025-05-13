# mindmap-cli/mindmap_cli/display_utils.py
import sys
import os

try:
    import colorama
    colorama.init() # Initialize colorama; on Windows, this wraps stdout/stderr
except ImportError:
    colorama = None

# ANSI escape codes for colors (optional, can be extended)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m' # Resets color
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Global toggle for colors (e.g., can be disabled for non-supporting terminals)
# USE_COLORS = True # Original
# If colorama is available, it handles Windows compatibility.
# If not, we disable colors on Windows if not in a known good terminal (like WT_SESSION).
if colorama:
    USE_COLORS = True
else:
    USE_COLORS = (os.name != 'nt') or ('WT_SESSION' in os.environ) or ('TERM' in os.environ and 'xterm' in os.environ['TERM'])

def force_enable_colors(enable: bool = True):
    """Allows external modules to force color enabling/disabling, bypassing isatty() for USE_COLORS part."""
    global USE_COLORS
    USE_COLORS = enable


def formatted_print(message: str, level: str = "INFO", indent: int = 0, use_prefix: bool = True):
    """
    Prints a formatted message with optional indentation, prefix, and color.
    Levels: INFO, SUCCESS, WARNING, ERROR, DEBUG, ACTION
    """
    prefix_map = {
        "INFO": "[INFO] ",
        "SUCCESS": "[SUCCESS] ",
        "WARNING": "[WARNING] ",
        "ERROR": "[ERROR] ",
        "DEBUG": "[DEBUG] ",
        "ACTION": "[ACTION] ", # For prompts or user actions
        "RESULT": "[RESULT] ",
        "DETAIL": "  -> ",     # For sub-details
        "USAGE": "",  # For help command usage lines
        "COMMAND_NAME": "",    # For command names in help list (no prefix, just color)
        "NONE": ""             # No prefix
    }
    
    color_map = {
        "INFO": Colors.OKBLUE,
        "SUCCESS": Colors.OKGREEN,
        "WARNING": Colors.WARNING,
        "ERROR": Colors.FAIL,
        "DEBUG": Colors.OKCYAN,
        "ACTION": Colors.HEADER,
        "RESULT": Colors.OKCYAN,
        "DETAIL": Colors.OKBLUE,
        "NONE": "",
        "USAGE": Colors.OKCYAN,
        "COMMAND_NAME": Colors.OKGREEN
    }

    prefix_str = prefix_map.get(level.upper(), "[INFO] ") if use_prefix else ""
    indent_str = "  " * indent # Two spaces per indent level

    output_message = f"{indent_str}{prefix_str}{message}"

    # For web terminal, isatty() will be false, but we still want colors if USE_COLORS is forced true.
    # So, the condition becomes: if USE_COLORS is true, then apply colors.
    # The original isatty() check is more for preventing colors in piped output to files locally.
    if USE_COLORS: 
        color_code = color_map.get(level.upper(), "")
        end_color_code = Colors.ENDC if color_code else ""
        # Apply color only to prefix if prefix exists, otherwise to whole message
        if prefix_str and use_prefix :
             colored_prefix = f"{color_code}{prefix_str}{Colors.ENDC}"
             output_message = f"{indent_str}{colored_prefix}{message}"
        elif color_code : # No prefix, but color the message
             output_message = f"{indent_str}{color_code}{message}{Colors.ENDC}"
        
    # Determine stream (stdout for most, stderr for errors/warnings)
    stream = sys.stderr if level.upper() in ["ERROR", "WARNING"] else sys.stdout
    
    print(output_message, file=stream)

# --- Example usage (not part of the module, just for testing) ---
if __name__ == "__main__":
    formatted_print("This is an informational message.")
    formatted_print("Action successful!", level="SUCCESS")
    formatted_print("Something might be wrong.", level="WARNING", indent=1)
    formatted_print("A critical error occurred!", level="ERROR")
    formatted_print("Debugging details here.", level="DEBUG", use_prefix=False, indent=2)
    formatted_print("User needs to do this.", level="ACTION")
    formatted_print("Search result item.", level="RESULT", indent=1)
    formatted_print("Further detail.", level="DETAIL", indent=2)
    formatted_print("Usage: command --option <value>", level="USAGE")
    formatted_print("  mycommand      Does something cool", level="COMMAND_NAME", use_prefix=False)

    # Test without color (e.g., if USE_COLORS = False)
    # USE_COLORS = False
    # print("\n--- Without Colors ---")
    # formatted_print("This is an informational message.")
    # formatted_print("Action successful!", level="SUCCESS")
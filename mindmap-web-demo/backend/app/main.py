#!/usr/bin/env python3
import sys
import os
import argparse

# Ensure the package can be found if running main.py directly from root
if __package__ is None and not hasattr(sys, "frozen"):
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # project_root = os.path.dirname(script_dir) # if main.py is in mindmap-cli/
    project_root = os.path.dirname(os.path.abspath(__file__)) # if main.py is in root alongside mindmap_cli package
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from mindmap_cli.cli import main_cli as one_shot_entry_point
from mindmap_cli.interactive_cli import interactive_session
from mindmap_cli.commands_core import detailed_help_messages # For checking one-shot commands
from mindmap_cli.display_utils import formatted_print # Added import

def main():
    # Known one-shot commands (keys from your help messages or a defined list)
    # These are commands that, if typed directly after 'python main.py', trigger one-shot mode.
    one_shot_command_names = set(detailed_help_messages.keys()) - {"exit", "quit", "pwd", "file"} # Interactive only commands

    # Top-level parser for --interactive and --file for interactive mode startup
    # It should not consume the actual one-shot commands and their arguments.
    startup_parser = argparse.ArgumentParser(description="MindMap CLI", add_help=False) # add_help=False here
    startup_parser.add_argument(
        '--interactive',
        action='store_true',
        help="Force run in interactive mode."
    )
    startup_parser.add_argument( # This -f is for interactive startup
        "-f", "--file",
        dest="startup_file", 
        help="Path to mind map file for interactive session OR for a one-shot command (if not overridden by one-shot's -f)."
    )
    startup_parser.add_argument(
        '--interactive-for-websocket',
        action='store_true',
        help="Run interactive mode optimized for WebSocket (no readline, basic prompts)."
    )
    
    # Parse only known args meant for startup_parser, leave the rest for one-shot or interactive
    parsed_startup_args, remaining_argv = startup_parser.parse_known_args()

    # Determine mode
    run_interactive = parsed_startup_args.interactive
    
    if parsed_startup_args.interactive_for_websocket:
        # For WebSocket, directly start interactive session.
        # Pass a flag to interactive_session if it needs to behave differently (e.g., no readline).
        interactive_session(initial_filepath_session=parsed_startup_args.startup_file, for_websocket=True)
    elif not run_interactive and remaining_argv and remaining_argv[0] in one_shot_command_names:
        # It looks like a one-shot command.
        # one_shot_entry_point will use its own full argparse on sys.argv.
        # We need to make sure sys.argv is what one_shot_entry_point expects.
        # If `python main.py -f file.json new "Title"` is run, startup_parser consumes -f.
        # one_shot_entry_point needs to see it too.
        # Simplest: one_shot_entry_point re-parses original sys.argv.
        one_shot_entry_point()
    else:
        # Default to interactive or if --interactive is specified
        if not parsed_startup_args.interactive and remaining_argv : # e.g. python main.py some_unknown_thing
             formatted_print(f"Unknown command '{remaining_argv[0]}' for one-shot mode. Starting interactive session.", level="WARNING")
        elif not parsed_startup_args.interactive :
             formatted_print("No specific command given, starting interactive session.", level="INFO")
        interactive_session(initial_filepath_session=parsed_startup_args.startup_file)

if __name__ == "__main__":
    main()
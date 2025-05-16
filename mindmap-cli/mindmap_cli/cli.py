# mindmap-cli/mindmap_cli/cli.py
import argparse
import sys
import os
from typing import Optional, Tuple
from .storage import get_default_filepath, load_map_from_file, save_map_to_file # For direct load/save here
from .mindmap import MindMap # For type hint
from .commands_core import (
    new_map_action, load_map_action, save_map_action, add_node_action,
    list_map_action, delete_node_action, search_map_action, edit_node_action,
    move_node_action, export_map_action, # Added CommandStatus
    get_general_help_text, get_specific_help_text, CommandStatus
)
from .display_utils import formatted_print

# This MindMap instance is loaded per one-shot command
current_mindmap_obj: Optional[MindMap] = None
current_map_filepath: Optional[str] = None

def handle_new(args):
    global current_mindmap_obj, current_map_filepath
    filepath = args.file if args.file else get_default_filepath()
    # new_map_action no longer takes a title for root creation.
    # The 'title' from argparse for 'new' in one-shot mode is now effectively unused
    # if --file is specified or get_default_filepath() is used.
    # We'll proceed to create an empty file at 'filepath'.
    status, mindmap, msg = new_map_action(filepath, args.force)
    
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        current_mindmap_obj = mindmap
        current_map_filepath = filepath
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

def handle_load(args): # Not typically a one-shot, but for consistency if file arg is given
    global current_mindmap_obj, current_map_filepath
    filepath = args.file if args.file else get_default_filepath()
    status, mindmap, msg = load_map_action(filepath)

    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        current_mindmap_obj = mindmap
        current_map_filepath = filepath
    elif status == CommandStatus.NOT_FOUND: # File not found is not an error for one-shot if it means "start empty"
        formatted_print(msg, level="INFO")
        current_mindmap_obj = MindMap() # Start with an empty map
        current_map_filepath = filepath
        formatted_print("(No existing map found, operations will be on a new in-memory map if not saved)", level="INFO")
    else: formatted_print(msg, level="ERROR"); sys.exit(1)

def _load_mindmap_for_command(filepath_arg: Optional[str]) -> Tuple[Optional[MindMap], Optional[str]]:
    """Helper to load mindmap for one-shot commands that need one."""
    operation_target_msg: str
    if filepath_arg:
        fpath = filepath_arg
        operation_target_msg = f"Operating on specified file: '{os.path.abspath(fpath)}'"
    else:
        fpath = get_default_filepath()
        operation_target_msg = f"No file specified (-f), using default: '{os.path.abspath(fpath)}'"

    fpath_abs = os.path.abspath(fpath)
    formatted_print(operation_target_msg, level="INFO")

    mindmap, load_msg = load_map_from_file(fpath_abs) # load_msg from load_map_from_file includes path

    if not mindmap and "not found" in load_msg.lower(): # File not found case
        formatted_print(load_msg, level="INFO") # e.g., "Info: File '...' not found."
        formatted_print(f"Operations will be on a new in-memory map. Save to persist to '{fpath_abs}'.", level="INFO")
        return MindMap(), fpath_abs
    elif not mindmap:
        formatted_print(load_msg, level="ERROR") # e.g., "Error: Could not decode..."
        sys.exit(1)
    
    formatted_print(load_msg, level="SUCCESS") # e.g., "Mind map loaded successfully from '...'"
    return mindmap, fpath_abs

def handle_add(args):
    mindmap, filepath = _load_mindmap_for_command(args.file)
    if not mindmap: return # _load handles exit

    status, new_node, msg = add_node_action(mindmap, args.text, args.parent_id)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        save_success, save_msg = save_map_to_file(mindmap, filepath)
        if not save_success:
            formatted_print(f"Error saving after add: {save_msg}", level="ERROR")
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

def handle_list(args):
    mindmap, _ = _load_mindmap_for_command(args.file)
    if not mindmap: return

    status, _, msg = list_map_action(mindmap)
    if status == CommandStatus.SUCCESS and msg == "Mind map is empty.":
        formatted_print(msg, level="INFO")
    elif status == CommandStatus.SUCCESS:
        mindmap.display() # Direct display
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)


def handle_delete(args):
    mindmap, filepath = _load_mindmap_for_command(args.file)
    if not mindmap: return

    confirm_root = False
    node_to_delete_obj = mindmap.get_node(args.node_id) # Get the node object
    if node_to_delete_obj and args.node_id in mindmap.root_ids: # Check if it's a root card
        if not args.yes: # Add a --yes flag to argparse for delete
            formatted_print(f"Deleting the root card '{node_to_delete_obj.text}' requires --yes confirmation for one-shot command.", level="ERROR")
            sys.exit(1)
        confirm_root = True
        
    status, _, msg = delete_node_action(mindmap, args.node_id, confirm_root_delete=confirm_root)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        save_success, save_msg = save_map_to_file(mindmap, filepath)
        if not save_success:
            formatted_print(f"Error saving after delete: {save_msg}", level="ERROR")
            # Consider if sys.exit(1) is needed here too
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

def handle_search(args):
    mindmap, _ = _load_mindmap_for_command(args.file)
    if not mindmap: return

    status, results, msg = search_map_action(mindmap, args.text)
    formatted_print(msg, level="INFO") # msg from search_map_action
    if status == CommandStatus.SUCCESS and results:
        for node, path_nodes in results:
            path_str = " -> ".join([n.text for n in path_nodes]) if path_nodes else "N/A (likely root or error)"
            formatted_print(f"Node: '{node.text}' (ID: {node.id}, Depth: {node.depth})", level="RESULT", use_prefix=False, indent=1) # Example, adjust prefix/level
            formatted_print(f"Path: {path_str}", level="DETAIL", use_prefix=False, indent=2)
def handle_edit(args):
    mindmap, filepath = _load_mindmap_for_command(args.file)
    if not mindmap: return

    status, _, msg = edit_node_action(mindmap, args.node_id, args.new_text)
    if status == CommandStatus.SUCCESS: # msg from edit_node_action
        formatted_print(msg, level="SUCCESS")
        save_success, save_msg = save_map_to_file(mindmap, filepath)
        if not save_success:
            formatted_print(f"Error saving after edit: {save_msg}", level="ERROR")
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

def handle_move(args):
    mindmap, filepath = _load_mindmap_for_command(args.file)
    if not mindmap: return

    status, _, msg = move_node_action(mindmap, args.node_id, args.new_parent_id)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        save_success, save_msg = save_map_to_file(mindmap, filepath)
        if not save_success:
            formatted_print(f"Error saving after move: {save_msg}", level="ERROR")
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

def handle_export(args):
    mindmap, _ = _load_mindmap_for_command(args.file)
    if not mindmap: return

    status, content, msg = export_map_action(mindmap, args.output_file)
    if status == CommandStatus.SUCCESS:
        if args.output_file: # If filepath was given, message already indicates success/failure of writing
            formatted_print(msg, level="INFO") # msg from export_map_action is usually about file write
        elif content: # No output_file, print content to console
            formatted_print("\n--- Exported Mind Map (Text Tree) ---", level="NONE", use_prefix=False)
            formatted_print(content, level="NONE", use_prefix=False)
            formatted_print("------------------------------------", level="NONE", use_prefix=False)
        else: # No content (e.g. empty map)
            formatted_print(msg, level="INFO")
    else: # Error from export_map_action
        formatted_print(msg, level="ERROR")
        sys.exit(1)


def handle_help(args):
    if args.command_name: # Specific command help
        command_name_val = args.command_name[0] if isinstance(args.command_name, list) else args.command_name
        help_text = get_specific_help_text(command_name_val)
        if "Unknown command" in help_text:
            formatted_print(help_text, level="ERROR")
            return

        lines = help_text.strip().split('\n')
        for i, line_content in enumerate(lines):
            if line_content.lower().startswith("usage:"):
                formatted_print(line_content, level="USAGE", use_prefix=True)
            else: # Description lines
                formatted_print(line_content, level="NONE", use_prefix=False, indent=1)
    else: # General help
        help_string = get_general_help_text()
        lines = help_string.strip().split('\n')
        if not lines: return

        formatted_print(lines[0], level="HEADER", use_prefix=False) # Title
        if len(lines) > 1:
            formatted_print(lines[1], level="INFO", use_prefix=False, indent=1) # Subtitle

        command_lines_started = False
        for line_content in lines[2:]:
            stripped_line = line_content.strip()
            if stripped_line and line_content.startswith("  "): # Command line
                command_lines_started = True
                formatted_print(line_content, level="COMMAND_NAME", use_prefix=False)
            elif command_lines_started and not stripped_line: # Empty line after commands
                formatted_print("", level="NONE", use_prefix=False)
            elif stripped_line: # Footer
                formatted_print(stripped_line, level="INFO", use_prefix=False, indent=1)
        formatted_print("\nUse 'python main.py <command> --help' for detailed command-specific options via argparse.", level="INFO", indent=1)

def main_cli():
    parser = argparse.ArgumentParser(description="MindMap CLI (One-shot)", add_help=False) # Disable default help if we use a help command
    parser.add_argument("-f", "--file", help="Path to the mind map file (JSON).")

    subparsers = parser.add_subparsers(dest="command", title="Available commands")
    if sys.version_info >= (3,7): subparsers.required = True

    # New
    p_new = subparsers.add_parser("new", help=get_specific_help_text("new").split('\n')[0])
    # The "title" argument for 'new' in one-shot mode is less relevant now as 'new' just creates an empty file.
    # It could be used to derive a filename if --file is not given, but current logic prioritizes --file or default.
    p_new.add_argument("filename_or_title", help="Filename for the new map (e.g., mymap.json). If --file is also used, --file takes precedence.")
    p_new.add_argument("--force", action="store_true", help="Overwrite if file exists.")
    p_new.set_defaults(func=handle_new)

    # Add
    p_add = subparsers.add_parser("add", help=get_specific_help_text("add").split('\n')[0])
    p_add.add_argument("text", help="Node text.")
    p_add.add_argument("-p", "--parent-id", help="Parent node ID. If omitted, creates a new root card.")
    p_add.set_defaults(func=handle_add)

    # List
    p_list = subparsers.add_parser("list", help=get_specific_help_text("list").split('\n')[0])
    p_list.set_defaults(func=handle_list)

    # Delete
    p_del = subparsers.add_parser("delete", help=get_specific_help_text("delete").split('\n')[0])
    p_del.add_argument("node_id", help="ID of node to delete.")
    p_del.add_argument("--yes", action="store_true", help="Confirm root node deletion (if applicable).") # For one-shot
    p_del.set_defaults(func=handle_delete)

    # Search
    p_search = subparsers.add_parser("search", help=get_specific_help_text("search").split('\n')[0])
    p_search.add_argument("text", help="Text to search.")
    p_search.set_defaults(func=handle_search)

    # Edit
    p_edit = subparsers.add_parser("edit", help=get_specific_help_text("edit").split('\n')[0])
    p_edit.add_argument("node_id", help="ID of node to edit.")
    p_edit.add_argument("new_text", help="New text for the node.")
    p_edit.set_defaults(func=handle_edit)

    # Move
    p_move = subparsers.add_parser("move", help=get_specific_help_text("move").split('\n')[0])
    p_move.add_argument("node_id", help="ID of node to move.")
    p_move.add_argument("new_parent_id", help="ID of new parent node.")
    p_move.set_defaults(func=handle_move)

    # Export
    p_export = subparsers.add_parser("export", help=get_specific_help_text("export").split('\n')[0])
    p_export.add_argument("output_file", nargs="?", help="Optional .txt file to save export.")
    p_export.set_defaults(func=handle_export)
    
    # Help
    p_help = subparsers.add_parser("help", help="Show help.", add_help=False) # Disable argparse help for this subcmd
    p_help.add_argument('command_name', nargs='*', help="Command to get help for.") # Changed to '*' for flexibility
    p_help.set_defaults(func=handle_help)

    # If no command is given, 'argparse' will show its own help if add_help=True on main parser
    # If add_help=False, we need to handle it.
    if len(sys.argv) == 1: # Just 'python main.py'
        formatted_print(get_general_help_text(), level="NONE", use_prefix=False)
        sys.exit(0)
    # If 'python main.py --help'
    if '--help' in sys.argv and len(sys.argv) == 2: # Basic check for top-level --help
        formatted_print(get_general_help_text(), level="NONE", use_prefix=False) # Show our custom general help
        parser.print_help() # Then show argparse's more detailed structure if desired
        sys.exit(0)


    parsed_args = parser.parse_args()
    if hasattr(parsed_args, 'func'):
        # Pass the whole parser to handlers if they need to print sub-command help
        parsed_args.func(parsed_args)
    else:
        # This path is less likely if subparsers.required = True and add_help=False handling is right
        formatted_print("No command specified or invalid command structure.", level="ERROR")
        parser.print_help()
        sys.exit(1)
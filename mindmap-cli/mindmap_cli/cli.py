# mindmap-cli/mindmap_cli/cli.py
import argparse
import sys
import os
import functools # Added for decorator
from typing import Optional, Tuple, Callable, Any # Added Callable, Any
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
current_mindmap_obj: Optional[MindMap] = None # This might become obsolete for one-shot commands
current_map_filepath: Optional[str] = None # This might become obsolete for one-shot commands

# Decorator for commands that operate on a mind map
def mindmap_command(func: Callable[[MindMap, str, argparse.Namespace], bool]):
    """
    Decorator to handle loading and saving of a mind map for a command.
    - Loads the mind map from the file specified in args.file or default.
    - If file not found, initializes a new MindMap.
    - Handles load errors and exits.
    - Calls the decorated function with the mindmap, filepath, and args.
    - If the decorated function returns True (indicating modification), saves the map.
    """
    @functools.wraps(func)
    def wrapper(args: argparse.Namespace) -> None:
        filepath_arg: Optional[str] = getattr(args, 'file', None)
        operation_target_msg: str
        
        if filepath_arg:
            fpath = filepath_arg
            operation_target_msg = f"Operating on specified file: '{os.path.abspath(fpath)}'"
        else:
            fpath = get_default_filepath()
            operation_target_msg = f"No file specified (-f), using default: '{os.path.abspath(fpath)}'"

        fpath_abs = os.path.abspath(fpath)
        formatted_print(operation_target_msg, level="INFO")

        mindmap_obj, load_msg = load_map_from_file(fpath_abs)

        if not mindmap_obj and "not found" in load_msg.lower():
            formatted_print(load_msg, level="INFO")
            formatted_print(f"Operations will be on a new in-memory map. Save to persist to '{fpath_abs}'.", level="INFO")
            mindmap_obj = MindMap()
        elif not mindmap_obj:
            formatted_print(load_msg, level="ERROR")
            sys.exit(1)
        else:
            formatted_print(load_msg, level="SUCCESS")

        # Call the actual command handler
        # It should return True if the map was modified and needs saving
        modified = func(mindmap_obj, fpath_abs, args)

        if modified and mindmap_obj is not None and fpath_abs is not None:
            save_success, save_msg = save_map_to_file(mindmap_obj, fpath_abs)
            if not save_success:
                formatted_print(f"Error saving after command: {save_msg}", level="ERROR")
            # else:
                # Optionally print save success message, though commands often print their own overall success
                # formatted_print(f"Mind map saved successfully to '{fpath_abs}'.", level="SUCCESS")
    return wrapper

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

    fpath_abs = os.path.abspath(fpath) # Kept for _load_mindmap_for_command, to be removed later if unused
    # ... rest of _load_mindmap_for_command ...
    # _load_mindmap_for_command is now removed as all relevant handlers use the decorator.

@mindmap_command
def handle_add(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles adding a new node to the mind map."""
    status, new_node, msg = add_node_action(mindmap, args.text, args.parent_id)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        return True  # Indicates modification, so decorator should save
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1) # Or return False and let main CLI decide if exit is needed for all errors

@mindmap_command
def handle_list(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles listing nodes in the mind map."""
    status, _, msg = list_map_action(mindmap) # Assuming list_map_action returns CommandStatus
    
    if status == CommandStatus.SUCCESS:
        if msg == "Mind map is empty.": # Specific message from list_map_action for empty map
            formatted_print(msg, level="INFO")
        else:
            # Assuming list_map_action itself doesn't print for SUCCESS but returns data/confirmation.
            # If list_map_action already prints, this display() might be redundant or for different formatting.
            # For now, keeping display() as per original logic.
            mindmap.display() # Direct display
            if msg and msg != "Mind map is empty.": # If there's any other success message (e.g. count)
                 formatted_print(msg, level="INFO")
    else: # ERROR or other non-SUCCESS states
        formatted_print(msg, level="ERROR")
        sys.exit(1) # Or return False
    
    return False # List does not modify the map

@mindmap_command
def handle_delete(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles deleting a node from the mind map."""
    confirm_root = False
    node_to_delete_obj = mindmap.get_node(args.node_id)
    if node_to_delete_obj and args.node_id in mindmap.root_ids:
        if not args.yes:
            formatted_print(f"Deleting the root card '{node_to_delete_obj.text}' requires --yes confirmation for one-shot command.", level="ERROR")
            sys.exit(1)
        confirm_root = True
        
    status, _, msg = delete_node_action(mindmap, args.node_id, confirm_root_delete=confirm_root)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        return True  # Indicates modification
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

@mindmap_command
def handle_search(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles searching for nodes in the mind map."""
    status, results, msg = search_map_action(mindmap, args.text)
    formatted_print(msg, level="INFO") 
    if status == CommandStatus.SUCCESS and results:
        for node, path_nodes in results:
            path_str = " -> ".join([n.text for n in path_nodes]) if path_nodes else "N/A (likely root or error)"
            formatted_print(f"Node: '{node.text}' (ID: {node.id}, Depth: {node.depth})", level="RESULT", use_prefix=False, indent=1)
            formatted_print(f"Path: {path_str}", level="DETAIL", use_prefix=False, indent=2)
    # If search itself fails (e.g., bad regex if that were a feature), it would be an error
    # But typically search returns empty results for no matches, which is a SUCCESS state.
    # Exiting only if search_map_action indicates a true error.
    if status == CommandStatus.ERROR:
        # msg should already be printed by formatted_print above
        sys.exit(1)
    return False # Search does not modify the map

@mindmap_command
def handle_edit(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles editing a node's text."""
    status, _, msg = edit_node_action(mindmap, args.node_id, args.new_text)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        return True  # Indicates modification
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

@mindmap_command
def handle_move(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles moving a node to a new parent."""
    status, _, msg = move_node_action(mindmap, args.node_id, args.new_parent_id)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        return True  # Indicates modification
    else:
        formatted_print(msg, level="ERROR")
        sys.exit(1)

@mindmap_command
def handle_export(mindmap: MindMap, filepath: str, args: argparse.Namespace) -> bool:
    """Handles exporting the mind map."""
    # The 'filepath' parameter here is the source mindmap file, not the export target.
    # args.output_file is the target for the export.
    status, content, msg = export_map_action(mindmap, args.output_file) 
    if status == CommandStatus.SUCCESS:
        if args.output_file: 
            formatted_print(msg, level="INFO") 
        elif content: 
            formatted_print("\n--- Exported Mind Map (Text Tree) ---", level="NONE", use_prefix=False)
            formatted_print(content, level="NONE", use_prefix=False)
            formatted_print("------------------------------------", level="NONE", use_prefix=False)
        else: 
            formatted_print(msg, level="INFO")
    else: 
        formatted_print(msg, level="ERROR")
        sys.exit(1)
    return False # Export does not modify the source mind map

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
    # The 'new' command now uses the global -f/--file for filepath, similar to other commands.
    p_new = subparsers.add_parser("new", help="Creates a new mind map, optionally using the path from -f.")
    p_new.add_argument("--force", action="store_true", help="Overwrite if file exists.")
    p_new.set_defaults(func=handle_new) # handle_new is not yet decorated

    # Add
    p_add = subparsers.add_parser("add", help=get_specific_help_text("add").split('\n')[0]) # Decorator handles file loading/saving
    p_add.add_argument("text", help="Node text.")
    p_add.add_argument("-p", "--parent-id", help="Parent node ID. If omitted, creates a new root card.")
    p_add.set_defaults(func=handle_add) # handle_add is now decorated

    # List
    p_list = subparsers.add_parser("list", help=get_specific_help_text("list").split('\n')[0]) # Decorator handles file loading
    p_list.set_defaults(func=handle_list) # handle_list is now decorated

    # Delete
    p_del = subparsers.add_parser("delete", help=get_specific_help_text("delete").split('\n')[0])
    p_del.add_argument("node_id", help="ID of node to delete.")
    p_del.add_argument("--yes", action="store_true", help="Confirm root node deletion (if applicable).") 
    p_del.set_defaults(func=handle_delete) # Decorated

    # Search
    p_search = subparsers.add_parser("search", help=get_specific_help_text("search").split('\n')[0])
    p_search.add_argument("text", help="Text to search.")
    p_search.set_defaults(func=handle_search) # Decorated

    # Edit
    p_edit = subparsers.add_parser("edit", help=get_specific_help_text("edit").split('\n')[0])
    p_edit.add_argument("node_id", help="ID of node to edit.")
    p_edit.add_argument("new_text", help="New text for the node.")
    p_edit.set_defaults(func=handle_edit) # Decorated

    # Move
    p_move = subparsers.add_parser("move", help=get_specific_help_text("move").split('\n')[0])
    p_move.add_argument("node_id", help="ID of node to move.")
    p_move.add_argument("new_parent_id", help="ID of new parent node.")
    p_move.set_defaults(func=handle_move) # Decorated

    # Export
    p_export = subparsers.add_parser("export", help=get_specific_help_text("export").split('\n')[0])
    p_export.add_argument("output_file", nargs="?", help="Optional .txt file to save export.")
    p_export.set_defaults(func=handle_export) # Decorated
    
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
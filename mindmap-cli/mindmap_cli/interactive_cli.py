# mindmap-cli/mindmap_cli/interactive_cli.py
import shlex
import sys
import os
from typing import List, Optional
from .models import Node
from .mindmap import MindMap # For type hint
from .storage import get_default_filepath # No direct load/save here
from .commands_core import (
    new_map_action, load_map_action, save_map_action, add_node_action,
    list_map_action, delete_node_action, search_map_action, edit_node_action,
    move_node_action, export_map_action, # Import detailed_help from core
    get_general_help_text, get_specific_help_text, CommandStatus, detailed_help_messages # Import detailed_help from core
)
from .display_utils import Colors, formatted_print, USE_COLORS

try:
    import readline
except ImportError:
    readline = None # Tab completion will be disabled if readline is not available

# Global state for interactive session
current_map: Optional[MindMap] = None
current_filepath: Optional[str] = None
current_node_id: Optional[str] = None
_rl_completion_matches: List[str] = []

def _save_current_map_interactive(operation_name_hint: str):
    """Saves the current map if it exists and has a filepath. For interactive mode."""
    global current_map, current_filepath
    if current_map and current_filepath:
        status, _, msg = save_map_action(current_map, current_filepath)
        if status != CommandStatus.SUCCESS:
            formatted_print(f"Error saving map after {operation_name_hint}: {msg}", level="ERROR")
        else:
            formatted_print(msg, level="SUCCESS") # Print save success message
    elif current_map and not current_filepath:
        formatted_print(f"Map modified by {operation_name_hint} but no file path set. Use 'save <filepath>' to save.", level="WARNING")
    # If no current_map, it's an issue with command logic before saving, handled by calling functions

# After any map change (load, new), reset to top-level context.
def _update_current_node_after_map_change():
    """Sets current_node_id to root if map is loaded and has a root, otherwise None."""
    global current_map, current_node_id
    current_node_id = None

def cmd_new(args_list: list[str]):
    global current_map, current_filepath, current_node_id
    title = None
    final_filepath_to_use = None
    force_interactive = False
    
    # --- Argument Parsing ---
    parsed_title_parts = []
    explicit_filepath_from_arg = None
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == "--file":
            if i + 1 < len(args_list):
                explicit_filepath_from_arg = args_list[i+1]
                i += 1
            else:
                formatted_print("--file option requires a filepath.", level="ERROR")
                return
        elif arg == "--force": force_interactive = True
        else: parsed_title_parts.append(arg)
        i += 1
    
    if not parsed_title_parts:
        formatted_print(get_specific_help_text("new"), level="NONE", use_prefix=False)
        return
    title = " ".join(parsed_title_parts)
    # --- End Argument Parsing ---

    if explicit_filepath_from_arg:
        final_filepath_to_use = os.path.abspath(explicit_filepath_from_arg) # User specified a path
    else: # No --file argument, so filename depends on title
        # Sanitize title to create a valid filename
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        sanitized_base = "".join(c if c in safe_chars else '_' for c in title.strip())
        if not sanitized_base: sanitized_base = "untitled" # Handle empty or all-invalid-char titles
        
        filename_from_title = f"{sanitized_base[:50]}.json" # Truncate for safety if title is very long

        # Use the directory part of the true default path (e.g., ~/.mindmap_cli/data/)
        default_storage_dir = os.path.dirname(get_default_filepath())
        final_filepath_to_use = os.path.join(default_storage_dir, filename_from_title)

    # new_map_action no longer takes a title for root creation
    status, mindmap_obj, msg = new_map_action(final_filepath_to_use, force_interactive)
    
    if status == CommandStatus.SUCCESS and mindmap_obj:
        formatted_print(msg, level="SUCCESS")
        current_map = mindmap_obj
        current_filepath = final_filepath_to_use # Update current_filepath
        _update_current_node_after_map_change()
    else:
        formatted_print(msg, level="ERROR")

def cmd_load(args_list: list[str]):
    global current_map, current_filepath, current_node_id

    filepath_to_load = None

    if not args_list: # No filename provided, show interactive chooser
        default_data_dir = os.path.dirname(get_default_filepath())
        available_files = []
        if os.path.exists(default_data_dir) and os.path.isdir(default_data_dir):
            available_files = sorted([f for f in os.listdir(default_data_dir) if f.endswith('.json') and os.path.isfile(os.path.join(default_data_dir, f))])

        if not available_files:
            formatted_print(f"No mind map files found in {default_data_dir}. Defaulting to '{os.path.basename(get_default_filepath())}'.", level="INFO")
            filepath_to_load = get_default_filepath() # Fallback to default if none found
        else:
            formatted_print("Available mind map files:", level="INFO")
            for i, fname in enumerate(available_files):
                formatted_print(f"  {i+1}. {fname}", level="NONE", use_prefix=False)
            formatted_print("Enter number to load, filename (from above list), full path, or '0' to cancel:", level="ACTION", use_prefix=False)
            
            try:
                choice_input = input("> ").strip()
                if not choice_input or choice_input == '0':
                    formatted_print("Load cancelled.", level="INFO")
                    return
                
                try: # Try to interpret as number
                    choice_num = int(choice_input)
                    if 1 <= choice_num <= len(available_files):
                        filepath_to_load = os.path.join(default_data_dir, available_files[choice_num - 1])
                    else:
                        formatted_print("Invalid number.", level="ERROR")
                        return
                except ValueError: # Not a number, treat as filename or path
                    # Check if it's one of the listed files first
                    if choice_input in available_files:
                        filepath_to_load = os.path.join(default_data_dir, choice_input)
                    elif f"{choice_input}.json" in available_files and not choice_input.endswith(".json"):
                        filepath_to_load = os.path.join(default_data_dir, f"{choice_input}.json")
                    else: # Assume it's a direct path (relative or absolute)
                        filepath_to_load = choice_input
            except EOFError:
                formatted_print("\nLoad cancelled.", level="INFO")
                return
    else: # Filename provided as argument
        if len(args_list) > 1:
            formatted_print(get_specific_help_text("load"), level="NONE", use_prefix=False)
            return
        filepath_to_load = args_list[0]

    final_fpath_abs = os.path.abspath(filepath_to_load)
    status, mindmap_obj, msg = load_map_action(final_fpath_abs)

    if status == CommandStatus.SUCCESS and mindmap_obj:
        formatted_print(msg, level="SUCCESS")
        current_map = mindmap_obj
        current_filepath = final_fpath_abs # Store absolute path
        _update_current_node_after_map_change()
        if not current_map.root_ids: # Check if there are any root cards
            formatted_print("Loaded map is empty.", level="INFO")
    elif status == CommandStatus.NOT_FOUND:
        formatted_print(msg, level="INFO")
        current_map = MindMap() # Initialize an empty map
        current_filepath = final_fpath_abs # Store absolute path
        current_node_id = None
    else:
        formatted_print(msg, level="ERROR")

def cmd_save(args_list: list[str]):
    global current_map, current_filepath
    if not current_map:
        formatted_print("No map loaded to save. Use 'new' or 'load'.", level="WARNING")
        return

    save_path_interactive: Optional[str] = current_filepath # Default to current file
    
    # --- Argument Parsing for -f ---
    if args_list:
        if len(args_list) == 2 and args_list[0] == "-f":
            save_path_interactive = os.path.abspath(args_list[1])
        else:
            # If arguments are provided but not in the '-f <filepath>' format
            formatted_print("Invalid arguments for save.", level="ERROR")
            formatted_print(get_specific_help_text("save"), level="NONE", use_prefix=False)
            return
    # --- End Argument Parsing ---

    # If no -f was provided, save_path_interactive remains current_filepath
    
    if not save_path_interactive:
        formatted_print("No filepath specified to save. Use 'save <filepath>'.", level="ERROR")
        return

    status, _, msg = save_map_action(current_map, os.path.abspath(save_path_interactive))
    print(msg)
    if status == CommandStatus.SUCCESS:
        current_filepath = save_path_interactive # Update current filepath on successful save to new loc

def cmd_go(args_list: list[str]): # New command for navigation
    global current_map, current_node_id
    if not current_map:
        formatted_print("No map loaded.", level="WARNING")
        return
    if not current_map.root_ids:
        formatted_print("Map is empty, cannot navigate.", level="WARNING")
        return

    if not args_list:
        # Show info about current node
        if current_node_id:
            current_node = current_map.get_node(current_node_id)
            if current_node:
                path_texts = current_map.get_node_path_texts(current_node_id)
                path_str = " -> ".join(path_texts) if path_texts else "N/A"
                formatted_print(f"Current node: '{current_node.text}' (ID: {current_node.id})", level="INFO")
                formatted_print(f"Path: {path_str}", level="DETAIL", use_prefix=False, indent=1)
                formatted_print(f"Depth: {current_node.depth}", level="DETAIL", use_prefix=False, indent=1)
                formatted_print(f"Parent ID: {current_node.parent_id if current_node.parent_id else 'None'}", level="DETAIL", use_prefix=False, indent=1)
                formatted_print(f"Children count: {len(current_node.children_ids)}", level="DETAIL", use_prefix=False, indent=1)
            else:
                 formatted_print(f"Internal error: Current node ID '{current_node_id}' not found in map.", level="ERROR")
                 _update_current_node_after_map_change() # Try to reset to a valid root/card
        else:
             formatted_print("Current node is not set (at root or map is empty).", level="INFO")
             _update_current_node_after_map_change() # Try to set to a valid root/card
        return

    target = args_list[0]
    if len(args_list) > 1:
        formatted_print(get_specific_help_text("go"), level="NONE", use_prefix=False)
        return

    if target == "..":
        if current_node_id is None or not current_map.root_ids:
             formatted_print("Cannot go up from an empty map or unset node.", level="WARNING")
             return
        current_node = current_map.get_node(current_node_id)
        if current_node and current_node.parent_id:
            current_node_id = current_node.parent_id
            parent_node = current_map.get_node(current_node_id) # Should exist
            if parent_node:
                formatted_print(f"Moved up to '{parent_node.text}' (ID: {current_node_id})", level="INFO")
            else: # Should not happen in a consistent map
                formatted_print(f"Moved up to parent ID '{current_node_id}' (node details not found).", level="WARNING")
        elif current_node and current_node.id in current_map.root_ids:
            current_node_id = None # Effectively go "out" of the card to the top level
            formatted_print("Current context is now top-level (no active card). Use 'go <card_id>' to enter a card.", level="INFO")
        else: # current_node_id is set, but node not found, or no parent_id (but not root)
             formatted_print("Cannot go up from this node (parent not found or current node invalid).", level="ERROR")
    elif target == "/":
        if current_map.root_ids:
            current_node_id = None # Go to top level, above all cards
            formatted_print(f"Moved to top level. {len(current_map.root_ids)} card(s) available. Use 'go <card_id>' or 'ls'.", level="INFO")
        else:
            formatted_print("Map has no root.", level="WARNING")
    else: # Target is assumed to be a node ID
        node_to_go = current_map.get_node(target)
        if node_to_go:
            current_node_id = node_to_go.id
            formatted_print(f"Moved to '{node_to_go.text}' (ID: {current_node_id})", level="INFO")
        else:
            formatted_print(f"Node with ID '{target}' not found.", level="ERROR")

def cmd_add(args_list: list[str]):
    global current_map, current_node_id
    if not current_map:
        formatted_print("No map loaded. Use 'new' or 'load'.", level="WARNING")
        return

    text_interactive = None; parent_id_interactive = None; text_parts_interactive = []
    i=0
    while i < len(args_list):
        if args_list[i] == "-p":
            if i + 1 < len(args_list):
                parent_id_interactive = args_list[i+1]
                i += 1
            else:
                formatted_print("-p option requires parent ID.", level="ERROR")
                return
        else: text_parts_interactive.append(args_list[i])
        i += 1
    if not text_parts_interactive:
        formatted_print(get_specific_help_text("add"), level="NONE", use_prefix=False)
        return
    text_interactive = " ".join(text_parts_interactive)
    
    # Use current_node_id as default parent if -p is not provided
    parent_id_to_use = parent_id_interactive if parent_id_interactive else current_node_id
    
    if not parent_id_to_use:
        # No -p and current_node_id is None (i.e., at top level)
        # add_node_action will handle this by creating a new root card.
        # parent_id_to_use remains None.
        formatted_print("No parent specified and not inside a card. Creating a new card.", level="INFO")

    status, new_node_obj, msg = add_node_action(current_map, text_interactive, parent_id_to_use) # Use parent_id_to_use
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        _save_current_map_interactive("add")
    else:
        formatted_print(msg, level="ERROR")

def cmd_list(args_list: list[str]): # ls alias will point here
    global current_map, current_node_id
    if not current_map:
        # No map loaded, try to list JSON files in the default data directory
        default_data_dir = os.path.dirname(get_default_filepath())
        formatted_print(f"No map loaded. Listing available .json files in default directory: {default_data_dir}", level="INFO")
        if os.path.exists(default_data_dir) and os.path.isdir(default_data_dir):
            json_files = [f for f in os.listdir(default_data_dir) if f.endswith('.json') and os.path.isfile(os.path.join(default_data_dir, f))]
            if json_files:
                formatted_print("Available mind map files:", level="INFO")
                for fname in sorted(json_files):
                    formatted_print(f"- {fname}", level="NONE", use_prefix=False, indent=1)
            else:
                formatted_print("No .json files found in the default data directory.", level="INFO", indent=1)
        else:
            formatted_print("Default data directory does not exist or is not accessible.", level="WARNING", indent=1)
        return
    
    if not current_map.root_ids:
        formatted_print(f"Current map '{os.path.basename(current_filepath)}' is empty. Use 'add \"Card Title\"' to create a new card (root).", level="INFO")
        return
    
    recursive_display = False
    # Basic argument parsing for -R. Assumes -R is the only potential argument for now.
    if "-R" in args_list:
        recursive_display = True

    if current_node_id is None:
        # At top level
        if recursive_display:
            formatted_print(f"Full map content for '{os.path.basename(current_filepath)}' (-R):", level="INFO")
            current_map.display() # Display the full tree for all cards
        else:
            formatted_print(f"Root Cards in '{os.path.basename(current_filepath)}':", level="INFO")
            if not current_map.root_ids:
                formatted_print("  (No root cards)", level="INFO", indent=1)
            else:
                for r_id in current_map.root_ids:
                    r_node = current_map.get_node(r_id)
                    if r_node:
                        formatted_print(f"- {r_node.text} (ID: {r_node.id})", level="NONE", use_prefix=False, indent=1)
                    else:
                        formatted_print(f"- [Error: Root ID {r_id} not found]", level="ERROR", indent=1)
        return

    current_node = current_map.get_node(current_node_id)
    if not current_node:
         formatted_print(f"Internal error: Current node ID '{current_node_id}' not found in map. Resetting to root.", level="ERROR")
         _update_current_node_after_map_change()
         if current_node_id: current_node = current_map.get_node(current_node_id)
         if not current_node: # Still no current node (e.g. map became empty)
             formatted_print("Cannot list children: current node is invalid and no root exists.", level="ERROR")
             return

    # Initialize children here to avoid UnboundLocalError
    children: Optional[List[Node]] = None 

    if recursive_display:
        formatted_print(f"Recursive listing for '{current_node.text}' (ID: {current_node.id}):", level="INFO")
        current_map.display_subtree(current_node_id)
        # After recursive display, we don't need to check 'children' variable further for this branch.
        return # Exit after recursive display
    else:
        # Default behavior: list direct children
        formatted_print(f"Children of '{current_node.text}' (ID: {current_node.id}):", level="INFO")
        children = current_map.get_children_nodes(current_node_id)

    if children is not None: # Only proceed if children was populated (i.e., not recursive display)
        if not children:
            formatted_print("  (No children)", level="INFO", indent=1)
        else:
            for child in children:
                formatted_print(f"- {child.text} (ID: {child.id})", level="NONE", use_prefix=False, indent=1)

def cmd_tree(args_list: list[str]): # New command for full tree
    global current_map
    if not current_map:
        formatted_print("No map loaded. Use 'new' or 'load'.", level="WARNING")
        return
    if not current_map.root_ids:
        formatted_print("Mind map is empty.", level="INFO")
        return

    formatted_print("Full Mind Map Tree:", level="INFO")
    current_map.display()

def cmd_delete(args_list: list[str]):
    global current_map
    if not current_map:
        formatted_print("No map loaded.", level="WARNING")
        return
    if not args_list or len(args_list) != 1:
        formatted_print(get_specific_help_text("delete"), level="NONE", use_prefix=False)
        return
    node_id_interactive = args_list[0]

    confirm_root_delete_interactive = False
    node_to_del = current_map.get_node(node_id_interactive)
    if node_to_del and node_id_interactive in current_map.root_ids:
        # Use formatted_print for the question part if desired, but input() itself is separate
        formatted_print(f"Are you sure you want to delete the root node '{node_to_del.text}' and clear the map? (yes/no): ", level="ACTION", use_prefix=False)
        confirm_input = input()
        if confirm_input.lower() == 'yes':
            confirm_root_delete_interactive = True
        else:
            formatted_print("Deletion cancelled.", level="INFO")
            return
            
    status, _, msg = delete_node_action(current_map, node_id_interactive, confirm_root_delete_interactive)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        _save_current_map_interactive("delete")
    else:
        formatted_print(msg, level="ERROR")

def cmd_search(args_list: list[str]):
    global current_map
    if not current_map: formatted_print("No map loaded.", level="WARNING"); return
    if not args_list: formatted_print(get_specific_help_text("search"), level="NONE", use_prefix=False); return
    search_text_interactive = " ".join(args_list)

    status, results_interactive, msg = search_map_action(current_map, search_text_interactive)
    formatted_print(msg, level="INFO") # Prints "Found X nodes" or "No nodes found"
    if status == CommandStatus.SUCCESS and results_interactive:
        for node, path_nodes in results_interactive:
            path_str = " -> ".join([n.text for n in path_nodes]) if path_nodes else "N/A"
            print(f"- Node: '{node.text}' (ID: {node.id}, Depth: {node.depth})\n  Path: {path_str}")

def cmd_edit(args_list: list[str]):
    global current_map
    if not current_map: formatted_print("No map loaded.", level="WARNING"); return

    node_id_to_edit: Optional[str] = None
    new_text_from_args: Optional[str] = None

    if not args_list: # User typed 'edit'
        if not current_node_id:
            formatted_print("Please navigate into a card/node or provide a node ID to edit.", level="WARNING")
            formatted_print(get_specific_help_text("edit"), level="NONE", use_prefix=False)
            return
        node_id_to_edit = current_node_id
    elif len(args_list) == 1: # User typed 'edit <node_id>'
        node_id_to_edit = args_list[0]
    elif len(args_list) >= 2: # User typed 'edit <node_id> "new text"'
        node_id_to_edit = args_list[0]
        new_text_from_args = " ".join(args_list[1:])
    else: # Should not happen due to above checks, but good for safety
        formatted_print(get_specific_help_text("edit"), level="NONE", use_prefix=False)
        return

    if node_id_to_edit is None: # Should be caught by earlier logic
        formatted_print("Node ID for editing is missing.", level="ERROR")
        return

    final_new_text: Optional[str] = new_text_from_args

    if final_new_text is None: # Interactive edit mode
        node_to_edit_obj = current_map.get_node(node_id_to_edit)
        if not node_to_edit_obj:
            formatted_print(f"Node with ID '{node_id_to_edit}' not found.", level="ERROR")
            return
        
        formatted_print(f"Current text: '{node_to_edit_obj.text}'", level="INFO")
        prompt_message = "Enter new text (or press Enter to cancel): "
        
        new_text_input = input(prompt_message).strip() # readline prefill is complex, simple prompt for now

        if not new_text_input:
            formatted_print("Edit cancelled.", level="INFO")
            return
        final_new_text = new_text_input

    status, _, msg = edit_node_action(current_map, node_id_to_edit, final_new_text)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        _save_current_map_interactive("edit")
    else:
        formatted_print(msg, level="ERROR")

def cmd_move(args_list: list[str]):
    global current_map
    if not current_map: formatted_print("No map loaded.", level="WARNING"); return
    if len(args_list) != 2: formatted_print(get_specific_help_text("move"), level="NONE", use_prefix=False); return
    node_id_to_move_interactive = args_list[0]
    new_parent_id_interactive = args_list[1]

    status, _, msg = move_node_action(current_map, node_id_to_move_interactive, new_parent_id_interactive)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        _save_current_map_interactive("move")
    else:
        formatted_print(msg, level="ERROR")

def cmd_export(args_list: list[str]):
    global current_map
    if not current_map:
        formatted_print("No map loaded.", level="WARNING")
        return
    export_filepath_interactive = args_list[0] if args_list else None

    status, content_interactive, msg = export_map_action(current_map, export_filepath_interactive)
    if status == CommandStatus.SUCCESS:
        if export_filepath_interactive:
            # msg from export_map_action already indicates success/failure of file write
            formatted_print(msg, level="INFO") 
        elif content_interactive: # No output_file, print content
            formatted_print("\n--- Exported Mind Map (Text Tree) ---", level="NONE", use_prefix=False)
            formatted_print(content_interactive, level="NONE", use_prefix=False)
            formatted_print("------------------------------------", level="NONE", use_prefix=False)
        else: # e.g. "Map is empty"
            formatted_print(msg, level="INFO")
    else: # Error from export action
        formatted_print(msg, level="ERROR")

def cmd_file(args_list: list[str]):
    global current_filepath, current_map, current_node_id # Add current_node_id
    if current_filepath:
        formatted_print(f"Current mind map file: {current_filepath}", level="INFO")
    else:
        formatted_print(f"No mind map file active. Default target: {get_default_filepath()}", level="INFO")
    
    if current_map and current_map.root_ids:
        if len(current_map.root_ids) == 1:
            first_root = current_map.get_node(current_map.root_ids[0])
            if first_root:
                formatted_print(f"Loaded map with root card: '{first_root.text}'", level="INFO")
        else:
            formatted_print(f"Loaded map with {len(current_map.root_ids)} root cards.", level="INFO")
        if current_node_id: # ADD THIS BLOCK
            current_node_obj = current_map.get_node(current_node_id)
            if current_node_obj:
                 path_texts = current_map.get_node_path_texts(current_node_id)
                 path_str = " -> ".join(path_texts) if path_texts else "N/A"
                 formatted_print(f"Current node: '{current_node_obj.text}' (ID: {current_node_id})", level="INFO", indent=1)
                 formatted_print(f"Path: {path_str}", level="DETAIL", use_prefix=False, indent=2)
            else: # current_node_id is set, but node not found
                 formatted_print(f"Current node ID '{current_node_id}' not found in map (may have been deleted).", level="WARNING", indent=1)
        elif current_map.root_ids: # Map has roots, but current_node_id is None
             formatted_print("Current context is top-level (no active card).", level="INFO", indent=1)
    elif current_map:
        formatted_print("A map is loaded, but it's empty.", level="INFO")
    else:
        formatted_print("No map currently loaded in memory.", level="INFO")

def cmd_help(args_list: list[str]):
    if not args_list: # General help
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
            elif command_lines_started and not stripped_line: # Empty line after commands (e.g., before footer)
                formatted_print("", level="NONE", use_prefix=False) # Preserve empty line
            elif stripped_line: # Footer or other non-command lines
                formatted_print(stripped_line, level="INFO", use_prefix=False, indent=1)
            # else: other empty lines, let them be skipped or handle if necessary
    else: # Specific command help
        command_name = args_list[0]
        help_text = get_specific_help_text(command_name)
        if "Unknown command" in help_text:
            formatted_print(help_text, level="ERROR")
            return

        lines = help_text.strip().split('\n')
        for i, line_content in enumerate(lines):
            if line_content.lower().startswith("usage:"):
                formatted_print(line_content, level="USAGE", use_prefix=True)
            else: # Description lines
                formatted_print(line_content, level="NONE", use_prefix=False, indent=1)

# Command mapping for interactive session
interactive_commands_map = {
    "new": cmd_new, "load": cmd_load, 
    "save": cmd_save,
    "export": cmd_export,
    "add": cmd_add,
    "list": cmd_list, "ls": cmd_list,
    "tree": cmd_tree,
    "go": cmd_go, "cd": cmd_go,
    "delete": cmd_delete, "del": cmd_delete,
    "search": cmd_search, "find": cmd_search,
    "edit": cmd_edit, 
    "move": cmd_move, "mv": cmd_move,
    "file": cmd_file, "pwd": cmd_file, 
    "help": cmd_help, "h": cmd_help,
    "exit": lambda args=None: sys.exit(0), "quit": lambda args=None: sys.exit(0),
}

def _command_completer(text: str, state: int) -> Optional[str]:
    """Readline completer function for interactive commands."""
    global _rl_completion_matches
    # If this is the first call for this text (state is 0)
    if state == 0:
        original_commands = list(interactive_commands_map.keys())
        if text:
            _rl_completion_matches = [cmd for cmd in original_commands if cmd.startswith(text)]
        else:
            # If no text, offer all commands (readline might call this for an empty line before space)
            _rl_completion_matches = original_commands[:]
    
    # Return the match for the current state
    try:
        return _rl_completion_matches[state]
    except IndexError:
        return None # No more matches

def setup_readline_completion():
    """Sets up readline for command completion if available."""
    if readline:
        readline.set_completer(_command_completer)
        # 'tab: complete' will complete the common prefix.
        # On a second tab press (if still ambiguous), it usually lists options.
        readline.parse_and_bind("tab: complete")

        # The following setting helps display all ambiguous completions on the first Tab press.
        # It might not be supported by all readline versions/bindings (e.g., older ones).
        try:
            readline.parse_and_bind("set show-all-if-ambiguous on")
        except Exception: # pragma: no cover
            pass # Silently ignore if the setting is not supported
        
        # Define what characters delimit words for completion. Space is good for commands.
        readline.set_completer_delims(" \t\n;")

def interactive_session(initial_filepath_session: Optional[str] = None):
    global current_map, current_filepath

    if initial_filepath_session:
        status, map_obj, msg = load_map_action(initial_filepath_session)
        if status == CommandStatus.SUCCESS and map_obj: current_map = map_obj; current_filepath = initial_filepath_session
        # load_map_action's message is handled by cmd_load if called, but here it's direct.
        # However, we don't want to print it here as the welcome messages below are more appropriate for session start.
    else:
        default_fpath = get_default_filepath()
        if os.path.exists(default_fpath):
            status, map_obj, msg = load_map_action(default_fpath)
            if status == CommandStatus.SUCCESS and map_obj: current_map = map_obj; current_filepath = default_fpath
            # Same as above, suppress direct message from load_map_action here.

    setup_readline_completion() # Setup completion before starting the input loop

    formatted_print("\nWelcome to MindMap CLI Interactive Mode!", level="HEADER", use_prefix=False)
    # Check if a map and filepath are active
    if current_map and current_filepath:
        # Now check if the map has any root cards
        if current_map.root_ids:
            first_root_node = current_map.get_node(current_map.root_ids[0]) if current_map.root_ids else None
            map_title_desc = f"'{first_root_node.text}' (and possibly others)" if first_root_node else f"{len(current_map.root_ids)} card(s)"
            formatted_print(f"Currently: Map with {map_title_desc} from '{current_filepath}'", level="INFO")
        else: # Map exists, filepath exists, but no root_ids (empty map)
            formatted_print(f"Currently: Empty map (no cards) from '{current_filepath}'", level="INFO")
    elif current_map and current_map.root_ids: # Has roots, but no current_node_id (e.g. at top level)
            formatted_print(f"Current context is top-level. Use 'go <card_id>' to enter a card.", level="INFO", indent=1)
    
    while True:
        try:
            # Constructing the colored prompt
            prompt_parts = []
            prompt_path_part = "" # For non-colored version
            if USE_COLORS and sys.stdout.isatty():
                prompt_parts.append(f"{Colors.OKGREEN}mindmap{Colors.ENDC} [")
                prompt_file_part = os.path.basename(current_filepath) if current_filepath else "no file"
                prompt_parts.append(f"{Colors.OKCYAN}{prompt_file_part}{Colors.ENDC}")
                
                # Add current node path to prompt
                if current_map and current_node_id:
                    current_node_obj = current_map.get_node(current_node_id) # Renamed for clarity
                    if current_node_obj: # Check if node still exists
                        path_texts = current_map.get_node_path_texts(current_node_id) # Needs get_node_path_texts in MindMap
                        if path_texts:
                            path_display = " / ".join(path_texts)
                            if len(path_display) > 30: # Arbitrary limit for prompt length
                                # Show last few elements if path is too long
                                path_display = ".../" + " / ".join(path_texts[-2:]) 
                            prompt_parts.append(f":{Colors.HEADER}{path_display}{Colors.ENDC}")
                prompt_parts.append("]> ")
                prompt_string = "".join(prompt_parts)
            else: # No colors
                prompt_file_part = os.path.basename(current_filepath) if current_filepath else "no file"
                if current_map and current_node_id:
                    current_node_obj = current_map.get_node(current_node_id)
                    if current_node_obj:
                         path_texts = current_map.get_node_path_texts(current_node_id)
                         if path_texts:
                             path_display = " / ".join(path_texts)
                             if len(path_display) > 30:
                                 path_display = ".../" + " / ".join(path_texts[-2:])
                             prompt_path_part = f":{path_display}"
                prompt_string = f"mindmap [{prompt_file_part}{prompt_path_part}]> "

            line = input(prompt_string)

            if not line.strip(): continue
            parts = shlex.split(line)
            command_name_input = parts[0].lower(); command_args_input = parts[1:]
            if command_name_input in interactive_commands_map:
                interactive_commands_map[command_name_input](command_args_input)
            else:
                formatted_print(f"Unknown command: '{command_name_input}'. Type 'help'.", level="ERROR")
        except EOFError:
            formatted_print("\nExiting...", level="INFO")
            break
        except KeyboardInterrupt:
            formatted_print("\nInterrupted. Type 'exit' or 'quit'.", level="WARNING")
            continue
        except SystemExit:
            formatted_print("Exiting application...", level="INFO")
            break
        except Exception as e:
            formatted_print(f"An unexpected error in interactive loop: {e}", level="ERROR")
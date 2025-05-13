# mindmap-cli/mindmap_cli/interactive_cli.py
import shlex
import sys
import os
from typing import List, Optional
from .mindmap import MindMap # For type hint
from .storage import get_default_filepath # No direct load/save here
from .commands_core import (
    new_map_action, load_map_action, save_map_action, add_node_action,
    list_map_action, delete_node_action, search_map_action, edit_node_action,
    move_node_action, export_map_action, # Import detailed_help from core
    get_general_help_text, get_specific_help_text, CommandStatus, detailed_help_messages # Import detailed_help from core
) # Import detailed_help from core
from .display_utils import Colors, formatted_print, USE_COLORS, force_enable_colors

try:
    import readline
except ImportError:
    readline = None # Tab completion will be disabled if readline is not available

# Global state for interactive session
current_map: Optional[MindMap] = None
current_filepath: Optional[str] = None
_rl_completion_matches: List[str] = [] # For readline completer state

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

def cmd_new(args_list: list[str]):
    global current_map, current_filepath
    title = None
    temp_filepath_interactive = current_filepath # Start with current, can be overridden
    force_interactive = False
    
    parsed_title_parts = []
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == "--file":
            if i + 1 < len(args_list):
                temp_filepath_interactive = args_list[i+1]
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
    
    if temp_filepath_interactive is None: temp_filepath_interactive = get_default_filepath()

    status, mindmap_obj, msg = new_map_action(title, temp_filepath_interactive, force_interactive)
    
    if status == CommandStatus.SUCCESS and mindmap_obj:
        formatted_print(msg, level="SUCCESS")
        current_map = mindmap_obj
        current_filepath = temp_filepath_interactive # new_map_action already saved it.
    else:
        formatted_print(msg, level="ERROR")

def cmd_load(args_list: list[str]):
    global current_map, current_filepath
    fpath = current_filepath if not args_list else args_list[0] # Default to current if no arg
    if not fpath : fpath = get_default_filepath() # If still none, use absolute default
    if len(args_list) > 1:
        formatted_print(get_specific_help_text("load"), level="NONE", use_prefix=False)
        return

    status, mindmap_obj, msg = load_map_action(fpath)

    if status == CommandStatus.SUCCESS and mindmap_obj:
        formatted_print(msg, level="SUCCESS")
        current_map = mindmap_obj
        current_filepath = fpath
        if not current_map.root:
            formatted_print("Loaded map is empty.", level="INFO")
    elif status == CommandStatus.NOT_FOUND: # File not found
        formatted_print(msg, level="INFO") # It's informational in interactive mode
        current_map = None 
        current_filepath = fpath # Or clear it: current_filepath = None
    else: # Other errors
        formatted_print(msg, level="ERROR")

def cmd_save(args_list: list[str]):
    global current_map, current_filepath
    if not current_map:
        formatted_print("No map loaded to save. Use 'new' or 'load'.", level="WARNING")
        return

    save_path_interactive = current_filepath
    if args_list:
        if len(args_list) == 1: save_path_interactive = args_list[0]
        else: formatted_print(get_specific_help_text("save"), level="NONE", use_prefix=False); return
    
    if not save_path_interactive:
        formatted_print("No filepath specified to save. Use 'save <filepath>'.", level="ERROR")
        return

    status, _, msg = save_map_action(current_map, save_path_interactive)
    print(msg)
    if status == CommandStatus.SUCCESS:
        current_filepath = save_path_interactive # Update current filepath on successful save to new loc

def cmd_add(args_list: list[str]):
    global current_map
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

    status, new_node_obj, msg = add_node_action(current_map, text_interactive, parent_id_interactive)
    if status == CommandStatus.SUCCESS:
        formatted_print(msg, level="SUCCESS")
        _save_current_map_interactive("add")
    else:
        formatted_print(msg, level="ERROR") # Or WARNING depending on add_node_action's typical errors

def cmd_list(args_list: list[str]):
    global current_map
    if not current_map:
        formatted_print("No map loaded. Use 'new' or 'load'.", level="WARNING")
        return
    
    status, _, msg = list_map_action(current_map)
    if status == CommandStatus.SUCCESS and msg == "Mind map is empty.":
        formatted_print(msg, level="INFO")
    elif status == CommandStatus.SUCCESS: # Implies map has content
        current_map.display()
    else: # Error from list_map_action (should be rare)
        formatted_print(msg, level="ERROR")

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
    if node_to_del and node_to_del == current_map.root:
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
    if len(args_list) < 2: formatted_print(get_specific_help_text("edit"), level="NONE", use_prefix=False); return
    node_id_interactive = args_list[0]
    new_text_interactive = " ".join(args_list[1:])

    status, old_text_val, msg = edit_node_action(current_map, node_id_interactive, new_text_interactive)
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
    global current_filepath, current_map
    if current_filepath:
        formatted_print(f"Current mind map file: {current_filepath}", level="INFO")
    else:
        formatted_print(f"No mind map file active. Default target: {get_default_filepath()}", level="INFO")
    
    if current_map and current_map.root:
        formatted_print(f"Loaded map title: {current_map.root.text}", level="INFO")
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
                formatted_print(line_content, level="USAGE", use_prefix=False)
            else: # Description lines
                formatted_print(line_content, level="NONE", use_prefix=False, indent=1)

# Command mapping for interactive session
interactive_commands_map = {
    "new": cmd_new, "load": cmd_load, "save": cmd_save, "add": cmd_add,
    "list": cmd_list, "delete": cmd_delete, "search": cmd_search,
    "edit": cmd_edit, "move": cmd_move, "export": cmd_export,
    "file": cmd_file, "pwd": cmd_file, "help": cmd_help, "h": cmd_help, # Added 'h' alias
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

def interactive_session(initial_filepath_session: Optional[str] = None, for_websocket: bool = False):
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

    if not for_websocket:
        setup_readline_completion() # Setup completion only if not for WebSocket

        formatted_print("\nWelcome to MindMap CLI Interactive Mode!", level="HEADER", use_prefix=False) # Or INFO
        if current_map and current_map.root and current_filepath:
            formatted_print(f"Currently: '{current_map.root.text}' from '{current_filepath}'", level="INFO")
        elif current_map and current_filepath: # Map loaded but empty
            formatted_print(f"Currently: Empty map from '{current_filepath}'", level="INFO")
        elif current_filepath: # Filepath set, but map not loaded or doesn't exist
            formatted_print(f"Target file: '{current_filepath}' (not loaded or empty)", level="INFO")
        else: # No file active
            formatted_print(f"No file active. Default target: {get_default_filepath()}", level="INFO")
        formatted_print("Type 'help' or 'h' for commands.", level="INFO")
    else:
        # For WebSocket, a minimal welcome or initial state might be sent.
        # The prompt is handled by the frontend.
        formatted_print("MindMap WebSocket session started.", level="INFO") # This goes to WS
        force_enable_colors(True) # Ensure colors are enabled for WebSocket output

    while True:
        try:
            prompt_string = "" # Prompt is handled by frontend for WebSocket
            if not for_websocket:
                # Constructing the colored prompt for local interactive mode
                prompt_parts = []
                if USE_COLORS and sys.stdout.isatty():
                    prompt_parts.append(f"{Colors.OKGREEN}mindmap{Colors.ENDC} [")
                    prompt_file_part = os.path.basename(current_filepath) if current_filepath else "no file"
                    prompt_parts.append(f"{Colors.OKCYAN}{prompt_file_part}{Colors.ENDC}")
                    if current_map and current_map.root:
                        prompt_title_part = f" ({Colors.HEADER}{current_map.root.text[:20]}...{Colors.ENDC})"
                        prompt_parts.append(prompt_title_part)
                    prompt_parts.append("]> ")
                    prompt_string = "".join(prompt_parts)
                else: # No colors
                    prompt_file_part = os.path.basename(current_filepath) if current_filepath else "no file"
                    prompt_title_part = f" ({current_map.root.text[:20]}...)" if current_map and current_map.root else ""
                    prompt_string = f"mindmap [{prompt_file_part}{prompt_title_part}]> "

            line = input(prompt_string)

            if not line.strip(): continue
            parts = shlex.split(line)
            command_name_input = parts[0].lower(); command_args_input = parts[1:]
            if command_name_input in interactive_commands_map:
                interactive_commands_map[command_name_input](command_args_input)
            else:
                formatted_print(f"Unknown command: '{command_name_input}'. Type 'help'.", level="ERROR")
        except EOFError:
            if not for_websocket: formatted_print("\nExiting...", level="INFO")
            # For WebSocket, EOF means the client's input stream to the subprocess closed.
            break
        except KeyboardInterrupt:
            if not for_websocket: formatted_print("\nInterrupted. Type 'exit' or 'quit'.", level="WARNING")
            else: formatted_print("\n[KeyboardInterrupt received by subprocess]", level="WARNING") # To WS
            continue
        except SystemExit:
            formatted_print("Exiting application...", level="INFO")
            break
        except Exception as e:
            formatted_print(f"An unexpected error in interactive loop: {e}", level="ERROR")
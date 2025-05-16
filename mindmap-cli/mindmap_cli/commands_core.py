# mindmap-cli/mindmap_cli/commands_core.py
import os
from .mindmap import MindMap, Node
from .storage import save_map_to_file, load_map_from_file, get_default_filepath
from typing import Optional, List, Tuple, Any, Dict

class CommandStatus:
    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"
    ALREADY_EXISTS = "already_exists"
    MAX_DEPTH_REACHED = "max_depth_reached"
    INVALID_OPERATION = "invalid_operation" # General invalid op like moving root

# Result tuple structure: (status: CommandStatus, data: Any, message: str)
# 'data' can be MindMap, Node, List[Node], etc., depending on the command.

def new_map_action(filepath: str, force: bool) -> Tuple[CommandStatus, Optional[MindMap], str]: # Add get_default_filepath import
    """Action to create a new, empty mind map file."""
    if os.path.exists(filepath) and not force:
        # Make the "already exists" message more concise if it's a default path
        display_path = filepath
        default_data_dir = os.path.dirname(get_default_filepath())
        # Check if the filepath is within the default data directory
        # os.path.abspath is used to normalize paths for comparison
        if os.path.abspath(os.path.dirname(filepath)) == os.path.abspath(default_data_dir):
            display_path = os.path.basename(filepath) # Just show filename

        return CommandStatus.ALREADY_EXISTS, None, f"File '{display_path}' already exists. Use --force to overwrite."
    
    mindmap = MindMap()
    # No root is created here, just an empty map structure

    success, msg = save_map_to_file(mindmap, filepath)
    if success:
        return CommandStatus.SUCCESS, mindmap, f"Created new empty mind map file: '{filepath}'."
    else:
        return CommandStatus.ERROR, mindmap, f"New map created in memory, but failed to save: {msg}"

def load_map_action(filepath: str) -> Tuple[CommandStatus, Optional[MindMap], str]:
    """Action to load a mind map."""
    mindmap, msg = load_map_from_file(filepath)
    if mindmap:
        return CommandStatus.SUCCESS, mindmap, msg
    else:
        # Check if msg indicates file not found vs actual error
        if "not found" in msg.lower(): # Heuristic
            return CommandStatus.NOT_FOUND, None, msg
        return CommandStatus.ERROR, None, msg

def save_map_action(mindmap: MindMap, filepath: str) -> Tuple[CommandStatus, None, str]:
    """Action to save the current mind map."""
    if not mindmap: # Should not happen if called correctly
        return CommandStatus.ERROR, None, "Error: No mind map object provided to save."
    success, msg = save_map_to_file(mindmap, filepath)
    if success:
        return CommandStatus.SUCCESS, None, msg
    else:
        return CommandStatus.ERROR, None, msg

def add_node_action(mindmap: MindMap, text: str, parent_id_str: Optional[str]) -> Tuple[CommandStatus, Optional[Node], str]:
    """Action to add a new node."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded to add a node to."

    if not parent_id_str: # No parent specified, create a new root card
        new_card_root = mindmap.add_new_root_card(text)
        if new_card_root:
            return CommandStatus.SUCCESS, new_card_root, f"Created new card '{text}' (ID: {new_card_root.id})."
        else: # Should not happen with add_new_root_card
            return CommandStatus.ERROR, None, f"Failed to create new card '{text}'."
    
    # Parent ID is specified, add as a child
    parent_node = mindmap.get_node(parent_id_str)
    if not parent_node:
        return CommandStatus.NOT_FOUND, None, f"Parent node with ID '{parent_id_str}' not found."
    
    parent_node_for_msg = f"node '{parent_node.text}' (ID: {parent_node.id})"

    # Depth check for adding a child
    if parent_node.depth >= MindMap.MAX_DEPTH:
         return CommandStatus.MAX_DEPTH_REACHED, None, f"Cannot add child to {parent_node_for_msg}. Parent is already at max depth ({MindMap.MAX_DEPTH}) for having children."

    new_node = mindmap.add_node(parent_id_str, text)
    if new_node:
        return CommandStatus.SUCCESS, new_node, f"Added node '{text}' (ID: {new_node.id}) under {parent_node_for_msg}."
    else:
        # This implies mindmap.add_node returned None, likely due to new node's depth exceeding MAX_DEPTH
        return CommandStatus.MAX_DEPTH_REACHED, None, f"Failed to add node '{text}' under {parent_node_for_msg}. Likely due to exceeding max depth ({MindMap.MAX_DEPTH})."
def list_map_action(mindmap: MindMap) -> Tuple[CommandStatus, None, str]:
    """Action to list/display the map. Display itself is a side effect."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded to list."
    # The actual printing is a side effect. This function confirms it can be done.
    # Or it could return a string representation for the CLI to print.
    # For now, CLI will call mindmap.display() directly.
    if not mindmap.root_ids:
        return CommandStatus.SUCCESS, None, "Mind map has no cards (roots)."
    return CommandStatus.SUCCESS, None, "Displaying map..." # CLI will call display()

def delete_node_action(mindmap: MindMap, node_id: str, confirm_root_delete: bool = False) -> Tuple[CommandStatus, None, str]:
    """Action to delete a node."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded."

    node_to_delete = mindmap.get_node(node_id)
    if not node_to_delete:
        return CommandStatus.NOT_FOUND, None, f"Node with ID '{node_id}' not found for deletion."

    if node_id in mindmap.root_ids and not confirm_root_delete:
        return CommandStatus.INVALID_OPERATION, None, f"Confirmation required to delete the root card '{node_to_delete.text}'."

    if mindmap.delete_node(node_id): # delete_node in MindMap handles recursive deletion
        return CommandStatus.SUCCESS, None, f"Deleted node ID '{node_id}' and its children."
    else: # Should not happen if node_to_delete was found
        return CommandStatus.ERROR, None, f"Failed to delete node ID '{node_id}'. Unknown error."

def search_map_action(mindmap: MindMap, search_text: str) -> Tuple[CommandStatus, List[Tuple[Node, Optional[List[Node]]]], str]:
    """Action to search nodes. Returns list of (node, path_nodes) tuples."""
    if not mindmap: return CommandStatus.ERROR, [], "Error: No mind map loaded to search."
    
    found_nodes = mindmap.find_nodes_by_text(search_text)
    results = []
    if not found_nodes:
        return CommandStatus.SUCCESS, [], f"No nodes found containing text '{search_text}'."

    for node in found_nodes:
        path = mindmap.get_node_path(node.id)
        results.append((node, path))
    
    return CommandStatus.SUCCESS, results, f"Found {len(results)} node(s) containing '{search_text}'."

def edit_node_action(mindmap: MindMap, node_id: str, new_text: str) -> Tuple[CommandStatus, Optional[str], str]:
    """Action to edit a node's text. Returns (status, old_text, message)."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded."

    node_to_edit = mindmap.get_node(node_id)
    if not node_to_edit:
        return CommandStatus.NOT_FOUND, None, f"Node with ID '{node_id}' not found for editing."

    old_text = node_to_edit.text
    node_to_edit.text = new_text
    return CommandStatus.SUCCESS, old_text, f"Node ID '{node_id}' text changed from '{old_text}' to '{new_text}'."

def move_node_action(mindmap: MindMap, node_id_to_move: str, new_parent_id: str) -> Tuple[CommandStatus, None, str]:
    """Action to move a node."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded."

    node_to_move = mindmap.get_node(node_id_to_move)
    new_parent_node = mindmap.get_node(new_parent_id)

    if not node_to_move: return CommandStatus.NOT_FOUND, None, f"Node to move (ID: {node_id_to_move}) not found."
    if not new_parent_node: return CommandStatus.NOT_FOUND, None, f"New parent card/node (ID: {new_parent_id}) not found."
    if node_to_move.id in mindmap.root_ids: return CommandStatus.INVALID_OPERATION, None, "Cannot move a root card. Delete and re-add if necessary."
    if new_parent_node.id == node_to_move.parent_id: return CommandStatus.INVALID_OPERATION, None, "Node is already under the specified parent."
    if new_parent_node.id == node_to_move.id: return CommandStatus.INVALID_OPERATION, None, "Cannot move a node under itself."


    # Circular dependency check
    current_check_node = new_parent_node
    while current_check_node:
        if current_check_node.id == node_to_move.id:
            return CommandStatus.INVALID_OPERATION, None, f"Cannot move node '{node_to_move.text}' under '{new_parent_node.text}'. This would create a circular dependency."
        current_check_node = mindmap.get_node(current_check_node.parent_id) if current_check_node.parent_id else None
    
    # Depth constraint check
    # This part needs the logic to calculate depths for the entire subtree being moved.
    # And ensure no part of it exceeds MindMap.MAX_DEPTH
    # For simplicity in this reconstruction, we'll assume a helper in MindMap or a local one.
    # Let's define a simplified check here for now. A full check is more involved.
    
    # Simplified depth check: new parent's depth + 1 for the moved node.
    # A real check needs to consider all children of the moved node.
    # This requires the same logic as in your previous 'cmd_move'
    temp_subtree_nodes_with_new_depths: Dict[str, int] = {}
    def get_max_depth_of_subtree_if_moved(root_of_subtree_id: str, new_base_depth_for_root: int) -> Tuple[Optional[int], str]:
        # This is the complex depth checking logic from your previous cmd_move
        # It should return (max_depth_achieved_or_None_if_fail, error_message_if_fail)
        # and populate temp_subtree_nodes_with_new_depths
        # For brevity, I will stub it and assume it works.
        # --- Start of StUBBED get_max_depth_of_subtree_if_moved ---
        # In a real implementation, this would be the full BFS/DFS depth calculation
        if not mindmap: return (None, "Mindmap not available for depth check") 
        node_root_of_subtree = mindmap.get_node(root_of_subtree_id)
        if not node_root_of_subtree: return (None, "Root of subtree not found for depth check")
        
        original_depth_of_root_subtree = node_root_of_subtree.depth
        max_achieved_depth = new_base_depth_for_root
        
        if new_base_depth_for_root > MindMap.MAX_DEPTH:
            return (None, f"Moving node '{node_root_of_subtree.text}' itself to depth {new_base_depth_for_root} exceeds max depth ({MindMap.MAX_DEPTH}).")

        q: list[str] = [root_of_subtree_id]
        visited_dfs: set[str] = set()

        while q:
            curr_id = q.pop(0)
            if curr_id in visited_dfs: continue
            visited_dfs.add(curr_id)

            curr_node_obj = mindmap.get_node(curr_id)
            if not curr_node_obj: continue

            relative_depth_in_subtree = curr_node_obj.depth - original_depth_of_root_subtree
            current_node_new_absolute_depth = new_base_depth_for_root + relative_depth_in_subtree
            
            temp_subtree_nodes_with_new_depths[curr_id] = current_node_new_absolute_depth

            if current_node_new_absolute_depth > MindMap.MAX_DEPTH:
                moved_node_text = mindmap.get_node(node_id_to_move).text if mindmap.get_node(node_id_to_move) else "Unknown"
                return (None, f"Moving '{moved_node_text}' would place its descendant '{curr_node_obj.text}' (ID: {curr_id}) at depth {current_node_new_absolute_depth}, exceeding max depth ({MindMap.MAX_DEPTH}).")
            
            max_achieved_depth = max(max_achieved_depth, current_node_new_absolute_depth)
            
            for child_id_val in curr_node_obj.children_ids:
                if child_id_val not in visited_dfs:
                    q.append(child_id_val)
        return (max_achieved_depth, "Depth check successful.")
        # --- End of STUBBED get_max_depth_of_subtree_if_moved ---

    potential_new_depth_of_moved_node = new_parent_node.depth + 1
    _, depth_check_msg = get_max_depth_of_subtree_if_moved(node_to_move.id, potential_new_depth_of_moved_node)
    if _ is None : # Indicates depth check failure
        return CommandStatus.MAX_DEPTH_REACHED, None, depth_check_msg

    # Perform the move in MindMap
    # 1. Remove from old parent's children list
    if node_to_move.parent_id:
        old_parent = mindmap.get_node(node_to_move.parent_id)
        if old_parent and node_to_move.id in old_parent.children_ids:
            old_parent.children_ids.remove(node_to_move.id)
    # 2. Update node's parent_id and add to new parent's children list
    node_to_move.parent_id = new_parent_node.id
    if node_to_move.id not in new_parent_node.children_ids:
        new_parent_node.children_ids.append(node_to_move.id)
    # 3. Update depths for the moved node and all its descendants
    for node_id_to_update, new_depth_value in temp_subtree_nodes_with_new_depths.items():
        node = mindmap.get_node(node_id_to_update)
        if node: node.depth = new_depth_value
            
    return CommandStatus.SUCCESS, None, f"Moved node '{node_to_move.text}' (ID: {node_to_move.id}) under '{new_parent_node.text}' (ID: {new_parent_id})."

def export_map_action(mindmap: MindMap, export_filepath: Optional[str]) -> Tuple[CommandStatus, Optional[str], str]:
    """Action to export map. Returns (status, export_content_or_None, message)."""
    if not mindmap or not mindmap.root_ids:
        return CommandStatus.SUCCESS, None, "Map has no cards, nothing to export."

    output_lines = []
    def generate_text_tree_recursive(node_id: str, indent_str: str = "", is_last_child: bool = True):
        node = mindmap.get_node(node_id)
        if not node: return
        connector = "└── " if is_last_child else "├── "
        output_lines.append(f"{indent_str}{connector}{node.text} (ID: {node.id})") # Added ID for clarity
        new_indent_str = indent_str + ("    " if is_last_child else "│   ")
        for i, child_id_val in enumerate(node.children_ids):
            generate_text_tree_recursive(child_id_val, new_indent_str, i == len(node.children_ids) - 1)

    for root_card_id in mindmap.root_ids:
        root_card_node = mindmap.get_node(root_card_id)
        if root_card_node:
            output_lines.append(f"{root_card_node.text} (ID: {root_card_node.id}) [CARD ROOT]")
            for i, child_id_val in enumerate(root_card_node.children_ids):
                generate_text_tree_recursive(child_id_val, "", i == len(root_card_node.children_ids) - 1)
            output_lines.append("-" * 20) # Separator

    export_content = "\n".join(output_lines)

    if export_filepath:
        try:
            with open(export_filepath, 'w', encoding='utf-8') as f:
                f.write(export_content)
            return CommandStatus.SUCCESS, None, f"Mind map exported as text tree to: {export_filepath}"
        except IOError as e:
            return CommandStatus.ERROR, None, f"Error writing export file '{export_filepath}': {e}"
    else:
        # Content will be printed by CLI layer
        return CommandStatus.SUCCESS, export_content, "Mind map export content generated."

# --- Help Messages (could also be in a separate help_utils.py) ---
detailed_help_messages = {
    "new": """Usage: new "Title" [--file <path>] [--force]\nCreates a new mind map.""",
    "load": """Usage: load [<path>]\nLoads a mind map from a JSON file.""",
    "save": """Usage: save [-f <filepath>]\nSaves the current mind map.
    save               : Saves to the current active file.
    save -f <filepath> : Saves to a different file path.""",
    "add": """Usage: add "Text" [-p PARENT_ID]\nAdds a new node. In interactive mode, defaults to adding under the current node if -p is not used.""",
    "edit": """Usage: edit [<NODE_ID>] ["New Text"]\nEdits the text of a node.
    edit <NODE_ID> "New Text" : Directly sets the new text.
    edit <NODE_ID>            : Prompts for new text for the specified node.
    edit                      : Prompts for new text for the current node.""",
    "move": """Usage: move <NODE_ID> <NEW_PARENT_ID>\nMoves a node under a new parent.""",
    "list": """Usage: list [-R]\nIn interactive mode: if inside a card, displays direct children of the current node. Use 'list -R' for a recursive listing from the current node. If at the top level (no card selected), displays the full map content. If no map is loaded, lists available .json files.""",
    "tree": """Usage: tree\nDisplays the full mind map structure from the root (primarily for interactive mode).""",
    "go": """Usage: go [<node_id> | .. | /]\nIn interactive mode, changes the current node context.
    go <node_id> : Navigates to the specified card/node.
    go ..        : Navigates to the parent of the current node.
    go /         : Navigates to the root node.
    go           : Shows information about the current node and its path.""",
    "delete": """Usage: delete <NODE_ID>\nDeletes a node and its children.""",
    "file": """Usage: file\nShows current file info. In interactive mode, also shows current node info. Alias: pwd""",
    "help": """Usage: help [<command>]\nDisplays help.""",
    "exit": """Usage: exit\nExits the application. Alias: quit""",
    "quit": """Usage: quit\nExits the application. Alias: exit"""
}

# Add aliases mapping to main command names
help_aliases = {
    "ls": "list",
    "cd": "go",
    "del": "delete",
    "find": "search",
    "mv": "move",
    "pwd": "file",
    "h": "help",
}

def get_general_help_text() -> str:
    lines = ["\nMindMap CLI - Available Commands", "Type 'help <command>' for more details."]
    main_commands = sorted(detailed_help_messages.keys())
    all_command_names = list(detailed_help_messages.keys()) + list(help_aliases.keys())
    max_len = max(len(cmd) for cmd in all_command_names) if all_command_names else 0

    for cmd_name in main_commands:
        summary = detailed_help_messages[cmd_name].split('\n')[0]
        aliases_for_this_cmd = sorted([alias for alias, target in help_aliases.items() if target == cmd_name])
        alias_info = f" (Aliases: {', '.join(aliases_for_this_cmd)})" if aliases_for_this_cmd else ""
        lines.append(f"  {cmd_name:<{max_len + 2}} {summary.replace('Usage: ', '')}{alias_info}")
    
    lines.append("\nNode IDs are UUIDs. Max depth is 2 (Root=0, Child=1, Grandchild=2).")
    lines.append("Interactive mode features:")
    lines.append("  'go'/'cd' for navigation (e.g., 'go <id>', 'go ..', 'go /').")
    lines.append("  'list'/'ls' shows children (use -R for recursive), full map (if at top level), or .json files (if no map loaded).")
    lines.append("  'tree' shows the full map.")
    return "\n".join(lines)

def get_specific_help_text(command_name: str) -> str:
    command_name = command_name.lower()
    main_command_name = help_aliases.get(command_name, command_name) # Resolve alias
    if main_command_name in detailed_help_messages: # Check main command name
        help_text = detailed_help_messages[main_command_name].strip()
        
        # Find all aliases pointing to this main command
        aliases_for_this_cmd = sorted([alias for alias, target in help_aliases.items() if target == main_command_name])
        if aliases_for_this_cmd:
            help_text += f"\n(Aliases: {', '.join(aliases_for_this_cmd)})"
            
        return help_text
    return f"Unknown command '{command_name}'. Type 'help' for a list."
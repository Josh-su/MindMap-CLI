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

def new_map_action(title: str, filepath: str, force: bool) -> Tuple[CommandStatus, Optional[MindMap], str]:
    """Action to create a new mind map."""
    if os.path.exists(filepath) and not force:
        return CommandStatus.ALREADY_EXISTS, None, f"File '{filepath}' already exists. Use --force to overwrite."
    
    mindmap = MindMap()
    try:
        mindmap.create_root(title) # This can't fail unless MindMap init has issues
    except ValueError as e: # Should not happen with a new MindMap
        return CommandStatus.ERROR, None, f"Error creating root: {e}"

    success, msg = save_map_to_file(mindmap, filepath)
    if success:
        return CommandStatus.SUCCESS, mindmap, f"Created new mind map '{title}' in '{filepath}'. Root ID: {mindmap.root.id if mindmap.root else 'N/A'}"
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

    parent_id_to_use = parent_id_str
    parent_node_for_msg = "root"

    if not parent_id_to_use:
        if mindmap.root:
            parent_id_to_use = mindmap.root.id
            parent_node_for_msg = f"root ('{mindmap.root.text}')"
        else:
            return CommandStatus.ERROR, None, "Map is empty. Cannot add node without a specified parent."
    
    if not parent_id_to_use: # Should not be reached if logic above is correct
        return CommandStatus.ERROR, None, "Internal error: parent_id_to_use became None."

    parent_node = mindmap.get_node(parent_id_to_use)
    if not parent_node:
        return CommandStatus.NOT_FOUND, None, f"Parent node with ID '{parent_id_to_use}' not found."
    parent_node_for_msg = f"node '{parent_node.text}' (ID: {parent_node.id})"

    # Check if PARENT is at max depth for having children (i.e., parent.depth == MAX_DEPTH)
    # The new node would be at parent.depth + 1.
    # The mindmap.add_node will check if new_node.depth > MAX_DEPTH.
    # This check here is mostly for a clearer message about the parent.
    if parent_node.depth >= MindMap.MAX_DEPTH:
         return CommandStatus.MAX_DEPTH_REACHED, None, f"Cannot add child to {parent_node_for_msg}. Parent is already at max depth ({MindMap.MAX_DEPTH}) for having children."

    new_node = mindmap.add_node(parent_id_to_use, text)
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
    if not mindmap.root:
        return CommandStatus.SUCCESS, None, "Mind map is empty." # It's successful, just nothing to show.
    return CommandStatus.SUCCESS, None, "Displaying map..." # CLI will call display()

def delete_node_action(mindmap: MindMap, node_id: str, confirm_root_delete: bool = False) -> Tuple[CommandStatus, None, str]:
    """Action to delete a node."""
    if not mindmap: return CommandStatus.ERROR, None, "Error: No mind map loaded."

    node_to_delete = mindmap.get_node(node_id)
    if not node_to_delete:
        return CommandStatus.NOT_FOUND, None, f"Node with ID '{node_id}' not found for deletion."

    if node_to_delete == mindmap.root and not confirm_root_delete:
        return CommandStatus.INVALID_OPERATION, None, f"Confirmation required to delete the root node '{node_to_delete.text}'. This will clear the map."

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
    if not new_parent_node: return CommandStatus.NOT_FOUND, None, f"New parent node (ID: {new_parent_id}) not found."
    if node_to_move == mindmap.root: return CommandStatus.INVALID_OPERATION, None, "Cannot move the root node."
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
    if not mindmap or not mindmap.root:
        return CommandStatus.SUCCESS, None, "Map is empty, nothing to export." # Successful, but empty.

    output_lines = []
    def generate_text_tree_recursive(node_id: str, indent_str: str = "", is_last_child: bool = True):
        node = mindmap.get_node(node_id)
        if not node: return
        connector = "└── " if is_last_child else "├── "
        output_lines.append(f"{indent_str}{connector}{node.text}")
        new_indent_str = indent_str + ("    " if is_last_child else "│   ")
        for i, child_id_val in enumerate(node.children_ids):
            generate_text_tree_recursive(child_id_val, new_indent_str, i == len(node.children_ids) - 1)

    output_lines.append(f"{mindmap.root.text} [ROOT]")
    for i, child_id_val in enumerate(mindmap.root.children_ids):
        generate_text_tree_recursive(child_id_val, "", i == len(mindmap.root.children_ids) - 1)
    
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
    "save": """Usage: save [<path>]\nSaves the current mind map.""",
    "add": """Usage: add "Text" [-p PARENT_ID]\nAdds a new node.""",
    "list": """Usage: list\nDisplays the current mind map structure.""",
    "delete": """Usage: delete <NODE_ID>\nDeletes a node and its children.""",
    "search": """Usage: search "Text"\nSearches for nodes by text.""",
    "edit": """Usage: edit <NODE_ID> "New Text"\nEdits the text of a node.""",
    "move": """Usage: move <NODE_ID> <NEW_PARENT_ID>\nMoves a node.""",
    "export": """Usage: export [<filepath.txt>]\nExports map as text tree.""",
    "file": """Usage: file\nShows current file info.""",
    "help": """Usage: help [<command>]\nDisplays help.""",
    "exit": """Usage: exit\nExits the application. Alias: quit""",
    "quit": """Usage: quit\nExits the application. Alias: exit"""
}

def get_general_help_text() -> str:
    lines = ["\nMindMap CLI - Available Commands", "Type 'help <command>' for more details."]
    cmd_list = sorted(detailed_help_messages.keys())
    max_len = max(len(cmd) for cmd in cmd_list) if cmd_list else 0
    for cmd_name in cmd_list:
        summary = detailed_help_messages[cmd_name].split('\n')[0] # First line as summary
        lines.append(f" {cmd_name:<{max_len + 2}} {summary.replace('Usage:', '').strip()}")
    lines.append("\nNode IDs are UUIDs. Max depth is 2 (Root=0, Child=1, Grandchild=2).")
    return "\n".join(lines)

def get_specific_help_text(command_name: str) -> str:
    command_name = command_name.lower()
    if command_name in detailed_help_messages:
        return detailed_help_messages[command_name].strip()
    return f"Unknown command '{command_name}'. Type 'help' for a list."
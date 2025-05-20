# mindmap-cli/mindmap_cli/mindmap.py
import sys
from typing import Dict, Optional, List, Tuple, Any
from .models import Node
from .display_utils import formatted_print

class MindMap:
    """Manages the mind map structure and operations."""
    MAX_DEPTH = 2 # Root (0) + Level 1 + Level 2

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.root_ids: List[str] = [] # Stores IDs of all top-level "cards"

    def _add_node_to_map(self, node: Node):
        if node.id in self.nodes:
            # This is more of a developer assertion; user-facing errors are usually handled higher up.
            # formatted_print(f"Internal Warning: Node ID {node.id} collision during _add_node_to_map.", level="WARNING")
            pass
        self.nodes[node.id] = node

    def add_new_root_card(self, text: str) -> Node:
        """Adds a new top-level card (a root node) to the map."""
        root_node = Node(text=text, depth=0)
        self._add_node_to_map(root_node)
        if root_node.id not in self.root_ids:
            self.root_ids.append(root_node.id)
        return root_node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def add_node(self, parent_id: str, text: str) -> Optional[Node]:
        parent_node = self.get_node(parent_id)
        if not parent_node:
            return None # Caller should handle "parent not found"

        new_depth = parent_node.depth + 1
        if new_depth > self.MAX_DEPTH:
             return None # Indicates failure due to depth, caller handles message

        new_node = Node(text=text, parent_id=parent_id, depth=new_depth)
        self._add_node_to_map(new_node) # Add to self.nodes
        parent_node.children_ids.append(new_node.id) # Link to parent
        return new_node

    def get_children_nodes(self, node_id: str) -> List[Node]:
        """Returns a list of child Node objects for a given node ID."""
        parent_node = self.get_node(node_id)
        if not parent_node:
            return []
        children = []
        for child_id_str in parent_node.children_ids:
            child_node_obj = self.get_node(child_id_str)
            if child_node_obj:
                children.append(child_node_obj)
            # else:
                # formatted_print(f"Warning: Child ID '{child_id_str}' listed in parent '{parent_node.text}' but node not found.", level="WARNING")
        return children

    def get_node_path(self, node_id: str) -> Optional[List[Node]]:
        """Returns a list of Node objects representing the path from a root to the given node."""
        node = self.get_node(node_id)
        if not node: return None
        
        path = []
        current: Optional[Node] = node
        visited_ids_in_path = set() # To prevent loops in case of data corruption

        while current:
            if current.id in visited_ids_in_path:
                formatted_print(f"Warning: Circular dependency detected in path for node {node_id}", level="WARNING")
                return None # Path is corrupted
            visited_ids_in_path.add(current.id)
            path.append(current)
            if current.parent_id is None: # Reached a root card
                break
            
            parent_of_current = self.get_node(current.parent_id)
            if parent_of_current is None:
                # This indicates an orphaned node if current.parent_id was not None.
                formatted_print(f"Warning: Inconsistent map data. Parent {current.parent_id} not found for node {current.id}", level="WARNING")
                return None # Path is broken
            current = parent_of_current
            
        return path[::-1] # Reverse to get path from root to node

    def get_node_path_texts(self, node_id: str) -> Optional[List[str]]:
        """Returns a list of node texts representing the path from root to node."""
        path_nodes = self.get_node_path(node_id)
        if path_nodes is None:
            return None
        return [node.text for node in path_nodes]

    def delete_node(self, node_id: str) -> bool:
        node_to_delete = self.get_node(node_id)
        if not node_to_delete:
            return False

        # If the deleted node was a root card, remove it from root_ids
        if node_to_delete.id in self.root_ids:
            self.root_ids.remove(node_to_delete.id)

        # Recursively delete children
        for child_id in list(node_to_delete.children_ids): # Iterate copy
            self.delete_node(child_id) # Recursive call

        # Remove from parent's children list
        if node_to_delete.parent_id:
            parent = self.get_node(node_to_delete.parent_id)
            if parent and node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        # Remove the node itself from the main dictionary
        if node_id in self.nodes:
            del self.nodes[node_id]
        
        # If all root cards are deleted, and nodes still exist (orphaned), clear them.
        if not self.root_ids and self.nodes:
            self.nodes.clear()

        return True

    def find_nodes_by_text(self, search_text: str) -> List[Node]:
        search_lower = search_text.lower()
        return [node for node in self.nodes.values() if search_lower in node.text.lower()]

    def _display_node(self, node_id: str, indent: str = "", is_last: bool = True):
        node = self.get_node(node_id)
        if not node: return
        connector = "└── " if is_last else "├── "
        formatted_print(f"{indent}{connector}{node.text} (ID: {node.id})", level="NONE", use_prefix=False)
        new_indent = indent + ("    " if is_last else "│   ")
        for i, child_id_str in enumerate(node.children_ids):
            self._display_node(child_id_str, new_indent, i == len(node.children_ids) - 1)

    def display_subtree(self, start_node_id: str):
        """Displays the subtree starting from the given node_id."""
        node = self.get_node(start_node_id)
        if not node:
            formatted_print(f"Node with ID '{start_node_id}' not found for subtree display.", level="ERROR")
            return

        # Print the starting node of the subtree (it's the "root" of this specific display)
        formatted_print(f"{node.text} (ID: {node.id})", level="NONE", use_prefix=False)
        
        # Now display its children recursively using the existing _display_node helper
        for i, child_id_str in enumerate(node.children_ids):
            self._display_node(child_id_str, "", i == len(node.children_ids) - 1)

    def display(self):
        if not self.root_ids:
            formatted_print("Mind map has no cards (roots).", level="INFO", use_prefix=False)
            return
        
        for i, root_id_in_list in enumerate(self.root_ids):
            root_node_obj = self.get_node(root_id_in_list)
            if root_node_obj:
                formatted_print(f"{root_node_obj.text} (ID: {root_node_obj.id}) [CARD ROOT]", level="NONE", use_prefix=False)
                for child_idx, child_id_str in enumerate(root_node_obj.children_ids):
                    self._display_node(child_id_str, "", child_idx == len(root_node_obj.children_ids) - 1)
            else:
                formatted_print(f"[Error: Root card ID '{root_id_in_list}' not found in nodes]", level="ERROR", use_prefix=False)
            
            if i < len(self.root_ids) - 1: # Add separator if not the last card
                formatted_print("-" * 20, level="NONE", use_prefix=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_ids": self.root_ids,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindMap':
        mind_map = cls()
        mind_map.root_ids = data.get("root_ids", [])
        nodes_data = data.get("nodes", {})

        if not mind_map.root_ids and not nodes_data: # Handle truly empty map case
            return mind_map

        for node_id_key, node_dict_val in nodes_data.items():
            try:
                # Reconstruct node from its dictionary representation
                node = Node.from_dict(node_dict_val)
                # Ensure the node's ID matches the key it was stored under, for consistency.
                if node.id != node_id_key:
                    # This might indicate an issue during saving or a corrupted file.
                    # For robustness, we could log a warning and use the key.
                    # formatted_print(f"Warning: Node ID mismatch for key '{node_id_key}' and node data ID '{node.id}'. Using key.", level="WARNING")
                    node.id = node_id_key # Prioritize the key from the 'nodes' dictionary
                mind_map._add_node_to_map(node)
            except KeyError as e:
                raise ValueError(f"Invalid node data: missing key {e} in node '{node_id_key}'") from e
            except Exception as e: # Catch other potential errors from Node.from_dict
                raise ValueError(f"Error reconstructing node '{node_id_key}': {e}") from e
        
        # Validate that all root_ids actually exist in the loaded nodes
        # and remove any root_ids that don't correspond to actual nodes.
        valid_root_ids = [r_id for r_id in mind_map.root_ids if r_id in mind_map.nodes]
        if len(valid_root_ids) != len(mind_map.root_ids):
            # formatted_print("Warning: Some root_ids were not found in the loaded nodes and have been removed.", level="WARNING")
            pass
        mind_map.root_ids = valid_root_ids
        
        return mind_map
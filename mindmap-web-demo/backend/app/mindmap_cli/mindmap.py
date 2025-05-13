# mindmap-cli/mindmap_cli/mindmap.py
import sys
from typing import Dict, Optional, List, Tuple, Any
from .models import Node
from .display_utils import formatted_print # Added import

class MindMap:
    """Manages the mind map structure and operations."""
    MAX_DEPTH = 2 # Root (0) + Level 1 + Level 2

    def __init__(self, root: Optional[Node] = None):
        self.nodes: Dict[str, Node] = {}
        self.root: Optional[Node] = None
        if root:
            self._add_node_to_map(root)
            self.root = root

    def _add_node_to_map(self, node: Node):
        if node.id in self.nodes:
            formatted_print(f"Node ID {node.id} collision.", level="WARNING")
        self.nodes[node.id] = node

    def create_root(self, text: str) -> Node:
        if self.root:
            raise ValueError("Mind map already has a root node.")
        root_node = Node(text=text, depth=0)
        self._add_node_to_map(root_node)
        self.root = root_node
        return root_node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def add_node(self, parent_id: str, text: str) -> Optional[Node]:
        parent_node = self.get_node(parent_id)
        if not parent_node:
            # Error handling should be done by the caller or a higher-level function
            # print(f"Error: Parent node with ID '{parent_id}' not found.", file=sys.stderr)
            return None

        # Depth check for the parent node is done by core_add_node before calling this
        # This function primarily creates and links the node.
        # if parent_node.depth >= self.MAX_DEPTH:
        #     print(f"Error: Cannot add child to node '{parent_node.text}'. Parent is already at max depth for having children.", file=sys.stderr)
        #     return None
        
        new_depth = parent_node.depth + 1
        if new_depth > self.MAX_DEPTH: # This is the crucial check for the new node itself
             # print(f"Error: Cannot add node '{text}'. Its depth ({new_depth}) would exceed max depth ({self.MAX_DEPTH}).", file=sys.stderr)
             return None # Indicates failure due to depth

        new_node = Node(text=text, parent_id=parent_id, depth=new_depth)
        self._add_node_to_map(new_node)
        parent_node.children_ids.append(new_node.id)
        return new_node

    def delete_node(self, node_id: str) -> bool:
        node_to_delete = self.get_node(node_id)
        if not node_to_delete:
            return False

        if node_to_delete == self.root:
            self.root = None # Deleting root clears the map effectively by orphaning everything

        # Recursively delete children (needed if we want to ensure full cleanup)
        for child_id in list(node_to_delete.children_ids): # Iterate copy
            self.delete_node(child_id)

        # Remove from parent's children list
        if node_to_delete.parent_id:
            parent = self.get_node(node_to_delete.parent_id)
            if parent and node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        if node_id in self.nodes:
            del self.nodes[node_id]
        
        if self.root is None and len(self.nodes) > 0:
            # If root got deleted, but other nodes remain, they are orphaned.
            # A robust system might try to find a new root or clear all nodes.
            # For this CLI, if root is gone, map is effectively empty for display.
            # We can choose to clear all nodes if root is deleted.
            self.nodes.clear() # If root is deleted, clear all nodes.

        return True

    def find_nodes_by_text(self, search_text: str) -> List[Node]:
        search_lower = search_text.lower()
        return [node for node in self.nodes.values() if search_lower in node.text.lower()]

    def get_node_path(self, node_id: str) -> Optional[List[Node]]:
        node = self.get_node(node_id)
        if not node: return None
        path = []
        current = node
        while current:
            path.append(current)
            if current.parent_id is None: break
            current = self.get_node(current.parent_id)
            if current is None and path[-1].parent_id is not None: return None # Inconsistency
        return path[::-1]

    def _display_node(self, node_id: str, indent: str = "", is_last: bool = True):
        node = self.get_node(node_id)
        if not node: return
        connector = "└── " if is_last else "├── "
        formatted_print(f"{indent}{connector}{node.text} (ID: {node.id})", level="NONE", use_prefix=False)
        new_indent = indent + ("    " if is_last else "│   ")
        for i, child_id in enumerate(node.children_ids):
            self._display_node(child_id, new_indent, i == len(node.children_ids) - 1)

    def display(self):
        if not self.root:
            formatted_print("Mind map is empty.", level="INFO", use_prefix=False) # Or NONE
            return
        formatted_print(f"{self.root.text} (ID: {self.root.id}) [ROOT]", level="NONE", use_prefix=False)
        for i, child_id in enumerate(self.root.children_ids):
            self._display_node(child_id, "", i == len(self.root.children_ids) - 1)

    def to_dict(self) -> Dict[str, Any]:
        if not self.root:
            return {"root_id": None, "nodes": {}}
        return {
            "root_id": self.root.id,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MindMap':
        mind_map = cls()
        root_id = data.get("root_id")
        nodes_data = data.get("nodes", {})
        if not root_id and not nodes_data: return mind_map # Empty map

        for node_id, node_data in nodes_data.items():
            try:
                node = Node.from_dict(node_data)
                if node.id != node_id: node.id = node_id # Ensure consistency
                mind_map._add_node_to_map(node)
            except KeyError as e:
                raise ValueError(f"Invalid node data: missing key {e} in node {node_id}") from e
        
        if root_id:
            root_node = mind_map.get_node(root_id)
            if not root_node:
                raise ValueError(f"Invalid map data: Root node ID '{root_id}' not found.")
            mind_map.root = root_node
        elif nodes_data: # Nodes exist but no root ID specified
            raise ValueError("Invalid map data: Nodes exist but no root_id specified.")
        return mind_map
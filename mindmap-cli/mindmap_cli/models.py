# mindmap-cli/mindmap_cli/models.py
import uuid
from typing import List, Dict, Any, Optional

class Node:
    """Represents a single node (idea) in the mind map."""
    def __init__(self, text: str, node_id: Optional[str] = None, parent_id: Optional[str] = None,
                 children_ids: Optional[List[str]] = None, depth: int = 0): # Add children_ids here
        self.id: str = node_id if node_id else str(uuid.uuid4())
        self.text: str = text
        self.parent_id: Optional[str] = parent_id
        self.children_ids: List[str] = children_ids if children_ids is not None else [] # Use provided list or empty list
        self.depth: int = depth

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the node to a dictionary."""
        return {
            '__node__': True, # Add marker for potential custom decoder
            "id": self.id,
            "text": self.text,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Deserializes a node from a dictionary."""
        # This method is used by MindMap.from_dict
        # It should correctly handle all attributes including children_ids
        return cls(
            text=data['text'],
            node_id=data['id'],
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', []), # Ensure children_ids is passed to __init__
            depth=data.get('depth', 0)
        )

    def __repr__(self) -> str:
        return f"Node(id={self.id}, text='{self.text}', depth={self.depth}, children={len(self.children_ids)})"
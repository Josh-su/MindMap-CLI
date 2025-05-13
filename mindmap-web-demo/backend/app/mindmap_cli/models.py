# mindmap-cli/mindmap_cli/models.py
import uuid
from typing import List, Dict, Any, Optional

class Node:
    """Represents a single node (idea) in the mind map."""
    def __init__(self, text: str, node_id: Optional[str] = None, parent_id: Optional[str] = None, depth: int = 0):
        self.id: str = node_id if node_id else str(uuid.uuid4())
        self.text: str = text
        self.parent_id: Optional[str] = parent_id
        self.children_ids: List[str] = []
        self.depth: int = depth

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the node to a dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "depth": self.depth,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Deserializes a node from a dictionary."""
        node = cls(
            text=data['text'],
            node_id=data['id'],
            parent_id=data.get('parent_id'),
            depth=data.get('depth', 0)
        )
        node.children_ids = data.get('children_ids', [])
        return node

    def __repr__(self) -> str:
        return f"Node(id={self.id}, text='{self.text}', depth={self.depth}, children={len(self.children_ids)})"
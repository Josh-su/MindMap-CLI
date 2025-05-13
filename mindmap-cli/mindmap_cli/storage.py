# mindmap-cli/mindmap_cli/storage.py
import json
import os
from typing import Optional, Tuple
from .mindmap import MindMap

DEFAULT_DATA_DIR = "data"
DEFAULT_FILENAME = "my_map.json"

def get_default_filepath() -> str:
    if not os.path.exists(DEFAULT_DATA_DIR):
        try:
            os.makedirs(DEFAULT_DATA_DIR)
        except OSError: # Fallback to current dir if data dir creation fails
            return DEFAULT_FILENAME
    return os.path.join(DEFAULT_DATA_DIR, DEFAULT_FILENAME)

def save_map_to_file(mindmap: MindMap, filepath: str) -> Tuple[bool, str]:
    """Saves the mind map to a JSON file. Returns (success_status, message)."""
    try:
        map_data = mindmap.to_dict()
        dir_name = os.path.dirname(filepath)
        if dir_name: os.makedirs(dir_name, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, indent=4, ensure_ascii=False)
        return True, f"Mind map saved successfully to '{filepath}'"
    except IOError as e:
        return False, f"Error: Could not write to file '{filepath}'. {e}"
    except TypeError as e:
        return False, f"Error: Could not serialize mind map data. {e}"
    except Exception as e:
        return False, f"An unexpected error occurred during saving: {e}"

def load_map_from_file(filepath: str) -> Tuple[Optional[MindMap], str]:
    """Loads a mind map from a JSON file. Returns (mindmap_object, message)."""
    if not os.path.exists(filepath):
        return None, f"Info: File '{filepath}' not found. Starting with an empty map or create new."
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
        mindmap = MindMap.from_dict(map_data)
        return mindmap, f"Mind map loaded successfully from '{filepath}'."
    except json.JSONDecodeError as e:
        return None, f"Error: Could not decode JSON from '{filepath}'. Invalid format? {e}"
    except (ValueError, KeyError) as e:
        return None, f"Error: Invalid map data format in '{filepath}'. {e}"
    except IOError as e:
        return None, f"Error: Could not read file '{filepath}'. {e}"
    except Exception as e:
        return None, f"An unexpected error occurred during loading: {e}"
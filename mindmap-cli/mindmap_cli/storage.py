# mindmap-cli/mindmap_cli/storage.py
import json
import os
from typing import Optional, Tuple
import sys 
from .mindmap import MindMap # Assuming MindMap class is in mindmap.py

DEFAULT_DATA_SUBDIR_NAME = "data" 
DEFAULT_FILENAME = "my_map.json"

def get_default_filepath() -> str:
    """
    Returns the default filepath for the mind map, which is DEFAULT_FILENAME
    in a subdirectory (DEFAULT_DATA_SUBDIR_NAME) located in the directory
    of the executed script (e.g., main.py).
    The directory structure will be created by save_map_to_file if needed.
    """
    try:
        script_path = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script_path)
    except Exception:
        # Fallback to current working directory if sys.argv[0] is problematic
        # This might still lead to permission issues if CWD is restricted.
        script_dir = os.getcwd() 

    data_dir_path = os.path.join(script_dir, DEFAULT_DATA_SUBDIR_NAME)
    return os.path.join(data_dir_path, DEFAULT_FILENAME)

def save_map_to_file(mindmap: MindMap, filepath: str) -> Tuple[bool, str]:
    """Saves the mind map to a JSON file. Returns (success_status, message)."""
    try:
        map_data = mindmap.to_dict()
        dir_name = os.path.dirname(filepath)
        if dir_name: # Ensure directory exists only if a directory path is part of filepath
            os.makedirs(dir_name, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, indent=4, ensure_ascii=False)
        return True, f"Mind map saved successfully to '{filepath}'"
    except IOError as e:
        return False, f"Error: Could not write to file '{filepath}'. {e}"
    except TypeError as e: # For issues with data that can't be serialized by json.dump
        return False, f"Error: Could not serialize mind map data. {e}"
    except Exception as e: # Catch-all for other unexpected errors
        return False, f"An unexpected error occurred during saving: {e}"

def load_map_from_file(filepath: str) -> Tuple[Optional[MindMap], str]:
    """Loads a mind map from a JSON file. Returns (mindmap_object_or_None, message)."""
    if not os.path.exists(filepath):
        return None, f"Info: File '{filepath}' not found. Starting with an empty map or create new."
    if not os.path.isfile(filepath): # Check if it's actually a file
        return None, f"Error: Path '{filepath}' is not a file."
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Check if file is empty before attempting to load JSON
            if os.fstat(f.fileno()).st_size == 0:
                # Return an empty MindMap object if the file is empty
                return MindMap(), f"Info: File '{filepath}' is empty. Loaded an empty mind map."
            map_data = json.load(f)
        
        # Use the MindMap.from_dict classmethod for deserialization
        mindmap = MindMap.from_dict(map_data)
        return mindmap, f"Mind map loaded successfully from '{filepath}'."
    except json.JSONDecodeError as e:
        return None, f"Error: Could not decode JSON from '{filepath}'. Invalid format? {e}"
    except (ValueError, KeyError) as e: # Catches errors from MindMap.from_dict or Node.from_dict
        return None, f"Error: Invalid map data format in '{filepath}'. {e}"
    except IOError as e:
        return None, f"Error: Could not read file '{filepath}'. {e}"
    except Exception as e: # Catch-all for other unexpected errors
        return None, f"An unexpected error occurred during loading: {e}"
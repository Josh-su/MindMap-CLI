# backend/app/api.py
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS # For Cross-Origin Resource Sharing

# --- Add project root to sys.path to find mindmap_cli ---
# This assumes api.py is in backend/app/ and mindmap_cli is in backend/app/mindmap_cli/
# Adjust if your structure is different.
current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir) # If api.py is one level down from where mindmap_cli package is
project_root = current_dir # If api.py is in the same directory as the mindmap_cli package folder

if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End sys.path modification ---

from app.mindmap_cli.mindmap import MindMap
from app.mindmap_cli.storage import get_default_filepath, save_map_to_file, load_map_from_file
from app.mindmap_cli.commands_core import (
    CommandStatus,
    new_map_action,
    load_map_action,
    save_map_action,
    add_node_action,
    list_map_action, # We'll adapt this for API output
    delete_node_action,
    search_map_action,
    edit_node_action,
    move_node_action,
    export_map_action
)

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# --- Global state for the API (simplified for local development) ---
# In a production multi-user environment, this would need to be handled
# per user session or by passing map identifiers.
api_current_map: MindMap | None = None
api_current_filepath: str | None = None
# --- End Global State ---

def get_map_as_dict(mindmap_instance: MindMap | None) -> dict | None:
    """Helper to convert MindMap to dict for API response, or return None."""
    if mindmap_instance and mindmap_instance.root:
        # We need a way to represent the tree structure for the 'list' equivalent
        # For now, let's return the full to_dict() which includes all nodes and root_id
        return mindmap_instance.to_dict()
    elif mindmap_instance: # Map exists but is empty
        return {"root_id": None, "nodes": {}}
    return None

# --- API Endpoints ---

@app.route('/map/new', methods=['POST'])
def api_new_map():
    global api_current_map, api_current_filepath
    data = request.json
    if not data or 'title' not in data:
        return jsonify({"status": CommandStatus.ERROR, "message": "Missing 'title' in request body"}), 400

    title = data['title']
    filepath = data.get('filepath', get_default_filepath())
    force = data.get('force', False)

    status, mindmap_obj, msg = new_map_action(title, filepath, force)

    if status == CommandStatus.SUCCESS and mindmap_obj:
        api_current_map = mindmap_obj
        api_current_filepath = filepath
        return jsonify({"status": status, "message": msg, "filepath": filepath, "map": get_map_as_dict(api_current_map)}), 201
    else:
        return jsonify({"status": status, "message": msg}), 400 # Or 409 if ALREADY_EXISTS

@app.route('/map/load', methods=['POST'])
def api_load_map():
    global api_current_map, api_current_filepath
    data = request.json
    filepath = data.get('filepath', get_default_filepath())
    if not filepath: # Should be caught by get_default_filepath, but good to check
         return jsonify({"status": CommandStatus.ERROR, "message": "Filepath is required."}), 400


    status, mindmap_obj, msg = load_map_action(filepath)

    if status == CommandStatus.SUCCESS and mindmap_obj:
        api_current_map = mindmap_obj
        api_current_filepath = filepath
        return jsonify({"status": status, "message": msg, "filepath": filepath, "map": get_map_as_dict(api_current_map)}), 200
    elif status == CommandStatus.NOT_FOUND:
        api_current_map = None # Or a new empty map if desired
        api_current_filepath = filepath # Keep track of the path for a potential 'new' or 'save'
        return jsonify({"status": status, "message": msg, "filepath": filepath}), 404
    else:
        return jsonify({"status": status, "message": msg}), 500

@app.route('/map/save', methods=['POST'])
def api_save_map():
    global api_current_map, api_current_filepath
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded to save."}), 400

    data = request.json
    # Allow overriding filepath on save, otherwise use current
    save_path = data.get('filepath', api_current_filepath)

    if not save_path:
        return jsonify({"status": CommandStatus.ERROR, "message": "No filepath specified or previously set to save."}), 400

    status, _, msg = save_map_action(api_current_map, save_path)

    if status == CommandStatus.SUCCESS:
        api_current_filepath = save_path # Update current path if save was successful
        return jsonify({"status": status, "message": msg, "filepath": api_current_filepath}), 200
    else:
        return jsonify({"status": status, "message": msg}), 500

@app.route('/map', methods=['GET']) # Corresponds to 'list'
def api_list_map():
    global api_current_map
    if not api_current_map:
        return jsonify({"status": CommandStatus.SUCCESS, "message": "No map loaded.", "map": None}), 200 # Or 404
    
    # list_map_action was mostly for CLI side-effect printing.
    # Here, we directly serialize the map.
    map_data = get_map_as_dict(api_current_map)
    if api_current_map.root:
        return jsonify({"status": CommandStatus.SUCCESS, "message": "Current map data.", "map": map_data, "filepath": api_current_filepath}), 200
    else:
        return jsonify({"status": CommandStatus.SUCCESS, "message": "Map is loaded but empty.", "map": map_data, "filepath": api_current_filepath}), 200


@app.route('/node/add', methods=['POST'])
def api_add_node():
    global api_current_map, api_current_filepath
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded to add a node to."}), 400

    data = request.json
    if not data or 'text' not in data:
        return jsonify({"status": CommandStatus.ERROR, "message": "Missing 'text' in request body"}), 400

    text = data['text']
    parent_id = data.get('parent_id') # Optional

    status, new_node_obj, msg = add_node_action(api_current_map, text, parent_id)

    if status == CommandStatus.SUCCESS and new_node_obj:
        # Auto-save after modification
        if api_current_filepath:
            s_status, _, s_msg = save_map_action(api_current_map, api_current_filepath)
            if s_status != CommandStatus.SUCCESS:
                msg += f" | Warning: Failed to auto-save: {s_msg}"
        else:
            msg += " | Warning: Map not auto-saved (no filepath)."
        return jsonify({"status": status, "message": msg, "node_id": new_node_obj.id, "map": get_map_as_dict(api_current_map)}), 201
    else:
        http_status = 400
        if status == CommandStatus.NOT_FOUND: http_status = 404
        elif status == CommandStatus.MAX_DEPTH_REACHED: http_status = 403 # Forbidden-like
        return jsonify({"status": status, "message": msg}), http_status

@app.route('/node/<node_id>', methods=['DELETE'])
def api_delete_node(node_id: str):
    global api_current_map, api_current_filepath
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded."}), 400

    # For API, root deletion might not need explicit confirm_root_delete from body,
    # or you could add a query param ?confirm_root=true
    confirm_root = False
    node_to_delete = api_current_map.get_node(node_id)
    if node_to_delete and node_to_delete == api_current_map.root:
        # For an API, you might decide that deleting root is always allowed or requires a special flag
        # For simplicity here, let's assume direct deletion is okay if it's the root.
        # Or, you could check for a query parameter:
        # confirm_root = request.args.get('confirm_root', 'false').lower() == 'true'
        confirm_root = True # Defaulting to true for API simplicity for now

    status, _, msg = delete_node_action(api_current_map, node_id, confirm_root_delete=confirm_root)

    if status == CommandStatus.SUCCESS:
        if api_current_filepath:
            s_status, _, s_msg = save_map_action(api_current_map, api_current_filepath)
            if s_status != CommandStatus.SUCCESS:
                msg += f" | Warning: Failed to auto-save: {s_msg}"
        else:
            msg += " | Warning: Map not auto-saved (no filepath)."
        return jsonify({"status": status, "message": msg, "map": get_map_as_dict(api_current_map)}), 200 # Or 204 No Content
    else:
        http_status = 400
        if status == CommandStatus.NOT_FOUND: http_status = 404
        return jsonify({"status": status, "message": msg}), http_status

@app.route('/node/<node_id>', methods=['PUT']) # For editing
def api_edit_node(node_id: str):
    global api_current_map, api_current_filepath
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded."}), 400

    data = request.json
    if not data or 'new_text' not in data:
        return jsonify({"status": CommandStatus.ERROR, "message": "Missing 'new_text' in request body"}), 400
    new_text = data['new_text']

    status, old_text_val, msg = edit_node_action(api_current_map, node_id, new_text)

    if status == CommandStatus.SUCCESS:
        if api_current_filepath:
            s_status, _, s_msg = save_map_action(api_current_map, api_current_filepath)
            if s_status != CommandStatus.SUCCESS:
                msg += f" | Warning: Failed to auto-save: {s_msg}"
        else:
            msg += " | Warning: Map not auto-saved (no filepath)."
        return jsonify({"status": status, "message": msg, "old_text": old_text_val, "map": get_map_as_dict(api_current_map)}), 200
    else:
        http_status = 400
        if status == CommandStatus.NOT_FOUND: http_status = 404
        return jsonify({"status": status, "message": msg}), http_status

@app.route('/node/move', methods=['POST'])
def api_move_node():
    global api_current_map, api_current_filepath
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded."}), 400

    data = request.json
    if not data or 'node_id' not in data or 'new_parent_id' not in data:
        return jsonify({"status": CommandStatus.ERROR, "message": "Missing 'node_id' or 'new_parent_id' in request body"}), 400
    
    node_id_to_move = data['node_id']
    new_parent_id = data['new_parent_id']

    status, _, msg = move_node_action(api_current_map, node_id_to_move, new_parent_id)

    if status == CommandStatus.SUCCESS:
        if api_current_filepath:
            s_status, _, s_msg = save_map_action(api_current_map, api_current_filepath)
            if s_status != CommandStatus.SUCCESS:
                msg += f" | Warning: Failed to auto-save: {s_msg}"
        else:
            msg += " | Warning: Map not auto-saved (no filepath)."
        return jsonify({"status": status, "message": msg, "map": get_map_as_dict(api_current_map)}), 200
    else:
        http_status = 400
        if status == CommandStatus.NOT_FOUND: http_status = 404
        elif status == CommandStatus.MAX_DEPTH_REACHED: http_status = 403
        elif status == CommandStatus.INVALID_OPERATION: http_status = 409 # Conflict
        return jsonify({"status": status, "message": msg}), http_status

@app.route('/map/search', methods=['GET'])
def api_search_map():
    global api_current_map
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded to search."}), 400
    
    search_text = request.args.get('text')
    if not search_text:
        return jsonify({"status": CommandStatus.ERROR, "message": "Missing 'text' query parameter"}), 400

    status, results, msg = search_map_action(api_current_map, search_text)
    
    # Convert Node objects in results to dicts for JSON serialization
    api_results = []
    if status == CommandStatus.SUCCESS and results:
        for node, path_nodes_list in results:
            api_results.append({
                "node": node.to_dict(),
                "path": [n.to_dict() for n in path_nodes_list] if path_nodes_list else []
            })

    return jsonify({"status": status, "message": msg, "results": api_results}), 200

@app.route('/map/export', methods=['GET'])
def api_export_map():
    global api_current_map
    if not api_current_map:
        return jsonify({"status": CommandStatus.ERROR, "message": "No map loaded to export."}), 400

    # For API, export_filepath is less common; usually, content is returned.
    # If you want to support server-side file saving, you could add a query param.
    status, content, msg = export_map_action(api_current_map, export_filepath=None)

    if status == CommandStatus.SUCCESS:
        if content:
            return jsonify({"status": status, "message": msg, "content": content}), 200
        else: # Map was empty
            return jsonify({"status": status, "message": "Map is empty, nothing to export.", "content": ""}), 200
    else: # Should not happen if map is loaded
        return jsonify({"status": status, "message": msg}), 500

@app.route('/map/file', methods=['GET'])
def api_get_file_info():
    global api_current_map, api_current_filepath
    info = {
        "filepath": api_current_filepath if api_current_filepath else get_default_filepath(),
        "is_loaded": api_current_map is not None,
        "map_title": api_current_map.root.text if api_current_map and api_current_map.root else None,
        "is_empty": api_current_map is not None and api_current_map.root is None
    }
    return jsonify({"status": CommandStatus.SUCCESS, "message": "Current file and map status.", "info": info}), 200

@app.route('/status', methods=['GET'])
def api_status_check():
    """A simple endpoint to check if the API is running."""
    return jsonify({"status": "ok", "message": "MindMap API is running."}), 200


if __name__ == '__main__':
    # Ensure the default data directory exists if storage.py creates it on get_default_filepath()
    # This is good practice if get_default_filepath() has side effects like dir creation.
    _ = get_default_filepath()
    
    # Attempt to load a default map on startup if it exists
    default_fpath_on_startup = get_default_filepath()
    if os.path.exists(default_fpath_on_startup):
        print(f"Attempting to load default map: {default_fpath_on_startup}")
        status, map_obj, msg = load_map_action(default_fpath_on_startup)
        if status == CommandStatus.SUCCESS and map_obj:
            api_current_map = map_obj
            api_current_filepath = default_fpath_on_startup
            print(f"Successfully loaded default map: {msg}")
        else:
            print(f"Could not load default map: {msg}")
    else:
        print(f"No default map found at {default_fpath_on_startup}. Starting with no map loaded.")

    app.run(debug=True, host='0.0.0.0', port=5001) # Changed port to 5001 to avoid common conflicts
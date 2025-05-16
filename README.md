# MindMap CLI

A command-line interface (CLI) tool for creating, managing, and saving simple mind maps.

## Features

* Create, load, and save mind maps (JSON format).
* Add, delete, edit, and move nodes.
* List the mind map structure.
* Search for nodes by text.
* Export map to a simple text tree.
* Operates in one-shot command mode or an interactive shell.
* Max depth of 3 levels (Root=0, Child=1, Grandchild=2).

## Project Structure
```
mindmap-cli/
├── main.py # Main entry point script
├── mindmap_cli/ # Source code package
│ ├── init.py
│ ├── models.py # Node class definition
│ ├── mindmap.py # MindMap class (tree management)
│ ├── storage.py # JSON save/load utilities
│ ├── commands_core.py # Centralized command logic and help texts
│ ├── display_utils.py # printing & formatting utilities 
│ ├── cli.py # One-shot command line interface (argparse)
│ └── interactive_cli.py # Interactive shell interface
├── data/ # Default directory for map files (created automatically)
│ └── my_map.json # Example map file
README.md # This file
```
## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Josh-su/MindMap-CLI
    cd mindmap-cli
    ```
2.  **Create a virtual environment (Recommended):**
    ```bash
    python -m venv .venv
    ```
3.  **Activate the virtual environment:**
    - On Windows:
        ```bash
        .venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
4.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Interactive Mode

Start the interactive shell:
```bash
python main.py
# or
python main.py --interactive
# or with a specific file
python main.py -f path/to/your_map.json
python main.py --interactive -f path/to/your_map.json
```
Once in the shell, type ```help``` for a list of commands, or ```help <command>``` for specific help.

### 2. One-Shot Mode

Execute commands directly from your terminal:
```bash
python main.py <command> [options_for_command]
# Global option for file:
python main.py -f path/to/map.json <command> [options_for_command]
```

## Example Workflow (Interactive Mode)

### 1. launch the cli & help
```
C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli>python main.py
[INFO] No specific command given, starting interactive session.
Welcome to MindMap CLI Interactive Mode!

mindmap [no file]> help
MindMap CLI - Available Commands
  Type 'help <command>' for more details.
  add      add "Text" [-p PARENT_ID]
  delete   delete <NODE_ID> (Aliases: del)
  edit     edit [<NODE_ID>] ["New Text"]
  exit     exit
  file     file (Aliases: pwd)
  go       go [<node_id> | .. | /] (Aliases: cd)
  help     help [<command>] (Aliases: h)
  list     list [-R] (Aliases: ls)
  load     load [<path>]
  move     move <NODE_ID> <NEW_PARENT_ID> (Aliases: mv)
  new      new "Title" [--file <path>] [--force]
  quit     quit
  save     save [-f <filepath>]
  tree     tree

  Node IDs are UUIDs. Max depth is 2 (Root=0, Child=1, Grandchild=2).
  Interactive mode features:
  'go'/'cd' for navigation (e.g., 'go <id>', 'go ..', 'go /').
  'list'/'ls' shows children (use -R for recursive), full map (if at top level), or .json files (if no map loaded).
  'tree' shows the full map.
```

### 2. Load or Create a new map
```
mindmap [no file]> load
[INFO] Available mind map files:
  1. savetest.json
  2. test.json
  3. test1.json
  4. title.json
Enter number to load, filename (from above list), full path, or '0' to cancel:
> 0
[INFO] Load cancelled.
```
```
mindmap [no file]> new test3
[SUCCESS] Created new empty mind map file: 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'.
```

### 3. Add nodes
```
mindmap [test3.json]> add Card1
[INFO] No parent specified and not inside a card. Creating a new card.
[SUCCESS] Created new card 'Card1' (ID: 104b167c-df16-479b-bcc1-e49190b79984).
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```
```
mindmap [test3.json]> add Card2
[INFO] No parent specified and not inside a card. Creating a new card.
[SUCCESS] Created new card 'Card2' (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38).
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```

### 4. Add child nodes
```
mindmap [test3.json]> add child1 -p 104b167c-df16-479b-bcc1-e49190b79984
[SUCCESS] Added node 'child1' (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f) under node 'Card1' (ID: 104b167c-df16-479b-bcc1-e49190b79984).
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```

### 4. List nodes / move one & relist
```
mindmap [test3.json]> list
[INFO] Root Cards in 'test3.json':
  - Card1 (ID: 104b167c-df16-479b-bcc1-e49190b79984)
  - Card2 (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38)
```
```
mindmap [test3.json]> tree
[INFO] Full Mind Map Tree:
Card1 (ID: 104b167c-df16-479b-bcc1-e49190b79984) [CARD ROOT]
└── child1 (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f)
--------------------
Card2 (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38) [CARD ROOT]
```
```
mindmap [test3.json]> move dc317b83-d73b-41ef-8154-ede54c27ef5f 3458a1e0-f88f-427e-8f2c-d08991b18c38
[SUCCESS] Moved node 'child1' (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f) under 'Card2' (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38).
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```
```
mindmap [test3.json]> tree
[INFO] Full Mind Map Tree:
Card1 (ID: 104b167c-df16-479b-bcc1-e49190b79984) [CARD ROOT]
--------------------
Card2 (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38) [CARD ROOT]
└── child1 (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f)
```

### 5. Go in a node & Edit a specfique node
```
mindmap [test3.json]> go 3458a1e0-f88f-427e-8f2c-d08991b18c38
[INFO] Moved to 'Card2' (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38)
```
```
mindmap [test3.json:Card2]> ls
[INFO] Children of 'Card2' (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38):
  - child1 (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f)
```
```
mindmap [test3.json:Card2]> edit dc317b83-d73b-41ef-8154-ede54c27ef5f
[INFO] Current text: 'child1'
Enter new text (or press Enter to cancel): child1.1
[SUCCESS] Node ID 'dc317b83-d73b-41ef-8154-ede54c27ef5f' text changed from 'child1' to 'child1.1'.
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```

### 6. Delete nodes
```
mindmap [test3.json]> tree
[INFO] Full Mind Map Tree:
Card1 (ID: 104b167c-df16-479b-bcc1-e49190b79984) [CARD ROOT]
--------------------
Card2 (ID: 3458a1e0-f88f-427e-8f2c-d08991b18c38) [CARD ROOT]
└── child1.1 (ID: dc317b83-d73b-41ef-8154-ede54c27ef5f)
```
```
mindmap [test3.json]> delete 3458a1e0-f88f-427e-8f2c-d08991b18c38
Are you sure you want to delete the root node 'Card2' ? (yes/no):
yes
[SUCCESS] Deleted node ID '3458a1e0-f88f-427e-8f2c-d08991b18c38' and its children.
[SUCCESS] Mind map saved successfully to 'C:\GitHub\Josh-su\MindMap-CLI\mindmap-cli\data\test3.json'
```
```
mindmap [test3.json]> tree
[INFO] Full Mind Map Tree:
Card1 (ID: 104b167c-df16-479b-bcc1-e49190b79984) [CARD ROOT]
```

### 7. go to the top level/root
```
mindmap [test3.json:Card2]> go /
[INFO] Moved to top level. 1 card(s) available. Use 'go <card_id>' or 'ls'.
```

### 8. Exit
```
mindmap [test3.json]> exit
[INFO] Exiting application...
```
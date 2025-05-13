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
│ ├── cli.py # One-shot command line interface (argparse)
│ └── interactive_cli.py # Interactive shell interface
├── data/ # Default directory for map files (created automatically)
│ └── my_map.json # Default map file
└── README.md # This file
```
## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd mindmap-cli
    ```
2.  **Prerequisites:**
    * Python 3.7+

## Usage

### Interactive Mode

Start the interactive shell:
```bash
python main.py
# or
python main.py --interactive
# or with a specific file
python main.py -f path/to/your_map.json
python main.py --interactive -f path/to/your_map.json
```
Once in the shell, type help for a list of commands, or help <command> for specific help.

### Example:
```
mindmap [my_map.json]> add "New Idea" -p <parent_node_id>
mindmap [my_map.json]> list
mindmap [my_map.json]> exit
```
## One-Shot Commands

Execute commands directly from your terminal:
```
python main.py <command> [options_for_command]
# Global option for file:
python main.py -f path/to/map.json <command> [options_for_command]
```
### Examples:
#### Create a new map (will use data/my_map.json or specified by -f)
```
python main.py new "My Project Ideas"
python main.py -f project.json new "Project X" --force
```

### Add a node (IDs are printed/listed)
```
python main.py -f project.json add "Core Feature" -p <root_id_of_project_x>
```

### List a map
```
python main.py -f project.json list
```

### Get help
```
python main.py help
python main.py help new
python main.py new --help # Argparse's help for 'new' command options
```
Available Commands (see help in interactive mode or python main.py help for more details):
new, load, save
add, list, delete, search, edit, move
export, file (interactive only for file status), help, exit/quit (interactive only)

## Example Workflow (One-Shot)

### 1. Create a new map
```
$ python main.py -f shopping.json new "Shopping List"
Created new mind map 'Shopping List' in 'shopping.json'. Root ID: a1b2...
```

### 2. Add categories
```
$ python main.py -f shopping.json add "Groceries" -p a1b2...

Added node 'Groceries' (ID: b2c3...) under node 'Shopping List' (ID: a1b2...).
```
```
$ python main.py -f shopping.json add "Hardware" -p a1b2...

Added node 'Hardware' (ID: c3d4...) under node 'Shopping List' (ID: a1b2...).
```

### 3. List
```
$ python main.py -f shopping.json list
Shopping List (ID: a1b2...) [ROOT]
├── Groceries (ID: b2c3...)
└── Hardware (ID: c3d4...)
```
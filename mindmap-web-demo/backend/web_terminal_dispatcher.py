# backend/web_terminal_dispatcher.py
import os
import sys
import shlex
import subprocess # Import the subprocess module

# Configuration
# Assuming this dispatcher script is in 'backend/' and main.py is in 'backend/app/main.py'
# The command the user types vs. the actual script path relative to CWD.
ALLOWED_COMMANDS = {
    "python app/main.py": ("app/main.py", ["--interactive-for-websocket"])
    # Add other allowed applications here if needed
    # "python utils/tool.py": ("utils/tool.py", ["--some-flag"])
}
PYTHON_EXECUTABLE = sys.executable

def clear_screen_and_home_cursor():
    """Prints ANSI escape codes to clear the screen and move cursor to top-left."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def launch_application(user_command_str: str):
    """
    Validates the user's command and attempts to execute the corresponding
    application as a child process, waiting for it to complete.
    """
    if user_command_str not in ALLOWED_COMMANDS:
        print(f"Error: Command '{user_command_str}' is not recognized or allowed.", file=sys.stderr)
        sys.stderr.flush()
        return False

    script_relative_path, script_args = ALLOWED_COMMANDS[user_command_str]

    # The CWD will be set by websocket_server.py to the 'backend' directory.
    # So, script_relative_path like "app/main.py" will be resolved correctly.
    full_script_path = os.path.abspath(script_relative_path)

    if not os.path.isfile(full_script_path):
        print(f"Error: Application script '{full_script_path}' not found on server.", file=sys.stderr)
        sys.stderr.flush()
        return False

    # Prepare arguments for subprocess.run
    run_args = [PYTHON_EXECUTABLE, full_script_path] + script_args

    try:
        clear_screen_and_home_cursor() # Clear screen before launching app
        # Flush output before starting the subprocess
        sys.stdout.flush()
        sys.stderr.flush()

        # Run the application as a child process.
        # stdin, stdout, stderr are inherited from the dispatcher,
        # which are already connected to the WebSocket.
        process = subprocess.run(
            run_args,
            # stdin, stdout, stderr are inherited by default.
            # If you needed to capture them separately for some reason:
            # stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
            check=False # Don't raise CalledProcessError for non-zero exit codes
        )
        # After the subprocess finishes, print a newline for clarity
        print() # Adds a blank line after the app finishes
        return True # Indicate that the app ran (or attempted to run)
    except OSError as e:
        print(f"Critical Error: Could not execute application '{user_command_str}'. Reason: {e}", file=sys.stderr)
        sys.stderr.flush()
        return False

if __name__ == "__main__":
    clear_screen_and_home_cursor() # Clear screen on initial dispatcher start
    print("Welcome to the MindMap Web Terminal.")
    print("You can run the following applications:")
    for cmd_key in ALLOWED_COMMANDS.keys():
        print(f"  - {cmd_key}")
    print("Type 'exit' or 'quit' to close the terminal.")
    sys.stdout.flush()

    while True:
        try:
            prompt = "web-shell> "
            command_line = input(prompt) # input() will get data from the WebSocket via stdin
            command_line = command_line.strip()

            if command_line.lower() in ["exit", "quit"]:
                print("Exiting web terminal dispatcher...")
                sys.stdout.flush()
                break

            launched = launch_application(command_line)
            if launched:
                # Application finished, reprint the dispatcher's prompt and available commands
                # (or a subset of the initial welcome)
                clear_screen_and_home_cursor() # Clear screen after app finishes
                print("\nApplication session ended. Returning to web-shell.")
                print("You can run the following applications:")
                for cmd_key in ALLOWED_COMMANDS.keys():
                    print(f"  - {cmd_key}")
                sys.stdout.flush()
            # If launch_application returned False, an error was printed, loop continues.

        except EOFError:
            print("\nConnection closed by client.", file=sys.stderr)
            sys.stderr.flush()
            break
        except KeyboardInterrupt: # Should ideally be handled by the connected main.py
            print("\nDispatcher interrupted. Exiting.", file=sys.stderr)
            sys.stderr.flush()
            break
        except Exception as e:
            print(f"An unexpected error occurred in the dispatcher: {e}", file=sys.stderr)
            sys.stderr.flush()
            break
    sys.exit(0)
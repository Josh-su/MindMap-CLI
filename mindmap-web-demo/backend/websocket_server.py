# backend/websocket_server.py
import asyncio
import os
import sys
import subprocess # Import standard subprocess module
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles # To serve your frontend

# --- Ensure mindmap_cli package can be found ---
# Adjust this path if your websocket_server.py is located elsewhere relative to the 'app' directory
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# path_to_app_dir should point to the 'app' directory *within* 'backend'
path_to_app_dir = os.path.join(current_script_dir, "app") # Corrected path

if path_to_app_dir not in sys.path:
    sys.path.insert(0, path_to_app_dir)
# ---

app = FastAPI()

# Path to your new dispatcher script
PATH_TO_DISPATCHER_PY = os.path.join(current_script_dir, "web_terminal_dispatcher.py")
PYTHON_EXECUTABLE = sys.executable # Use the same python interpreter

async def stream_subprocess_io(websocket: WebSocket, process: subprocess.Popen):
    """Helper to stream IO between WebSocket and subprocess."""
    loop = asyncio.get_running_loop()

    async def forward_stdin():
        try:
            # process.stdin is a synchronous file-like object
            # We need to write to it in a way that doesn't block the event loop
            while True:
                data = await websocket.receive_text()
                if process.stdin and not process.stdin.closed:
                    # Ensure write and flush are non-blocking for the event loop
                    await loop.run_in_executor(
                        None, lambda: (process.stdin.write(data.encode()), process.stdin.flush())
                    )
                else:
                    break
        except WebSocketDisconnect:
            print("Client disconnected (stdin).")
        except Exception as e:
            print(f"Stdin forwarding error: {e}")
        # finally:
            # Closing stdin is usually handled by the subprocess itself when it expects no more input
            # or when the process terminates. Forcibly closing here might be premature.
            # if process.stdin and not process.stdin.closed:
            #     process.stdin.close()

    async def forward_stream_to_ws(stream, stream_name: str):
        try:
            # stream is a synchronous file-like object (e.g., process.stdout)
            # We need to read from it without blocking the event loop.
            while True:
                line_bytes = await loop.run_in_executor(None, stream.readline)
                if not line_bytes: # EOF
                    break
                await websocket.send_text(line_bytes.decode(errors='replace'))
            print(f"{stream_name} stream ended.")
        except WebSocketDisconnect:
            print(f"Client disconnected ({stream_name}).")
        except Exception as e:
            print(f"Error forwarding {stream_name}: {e}")

    stdin_task = asyncio.create_task(forward_stdin())
    stdout_task = asyncio.create_task(forward_stream_to_ws(process.stdout, "stdout"))
    stderr_task = asyncio.create_task(forward_stream_to_ws(process.stderr, "stderr"))

    try:
        # Wait for the I/O tasks to complete.
        # process.wait() is blocking, so run it in an executor if needed,
        # or rely on I/O tasks finishing when the process pipes close.
        await asyncio.gather(stdin_task, stdout_task, stderr_task)
    except WebSocketDisconnect:
        print("WebSocket disconnected during process IO.")
    finally:
        for task in [stdin_task, stdout_task, stderr_task]:
            if not task.done():
                task.cancel()
        if process.returncode is None:
            try:
                print("Terminating subprocess due to WebSocket closure or error.")
                process.terminate()
                # process.wait() is blocking, run in executor
                await loop.run_in_executor(None, process.wait, 5.0) # timeout for wait
            except subprocess.TimeoutExpired:
                print("Subprocess terminate timed out, killing.")
                process.kill()
                await loop.run_in_executor(None, process.wait)
            except Exception as e_term:
                print(f"Error during subprocess termination: {e_term}")

        # Ensure process.wait() is called to clean up resources if not already done
        if process.returncode is None: await loop.run_in_executor(None, process.wait)
        print(f"Subprocess exited with {process.returncode if process.returncode is not None else 'unknown (was killed or error)'}")

@app.websocket("/ws")
async def websocket_terminal_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"WebSocket connection accepted from: {websocket.client}")

    try:
        # Command to run the dispatcher script.
        # The dispatcher will then handle launching the actual main.py.
        command = [PYTHON_EXECUTABLE, PATH_TO_DISPATCHER_PY]

        # Use standard subprocess.Popen, run in a thread to avoid blocking
        # Popen itself is not async, but its I/O can be handled asynchronously.
        loop = asyncio.get_running_loop()
        process = await loop.run_in_executor(
            None,  # Uses default ThreadPoolExecutor
            lambda: subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=current_script_dir,
                # bufsize=0 for unbuffered, or 1 for line-buffered if that helps
            )
        )
        print(f"Started subprocess for {websocket.client} with PID {process.pid}")

        await stream_subprocess_io(websocket, process)

    except WebSocketDisconnect:
        print(f"Client {websocket.client} disconnected.")
    except Exception as e:
        import traceback
        print(f"Error in WebSocket endpoint: {e}\n{traceback.format_exc()}")
        try:
            await websocket.close(code=1011)
        except RuntimeError:
            pass # Already closed
    finally:
        print(f"WebSocket connection with {websocket.client} processing finished.")

# Serve your frontend static files (index.html, style.css, script.js)
# Place your frontend files in a 'frontend_static' directory sibling to this script,
# or adjust the path.
PATH_TO_FRONTEND_STATIC = os.path.join(os.path.dirname(current_script_dir), "frontend")
if os.path.exists(PATH_TO_FRONTEND_STATIC):
    app.mount("/", StaticFiles(directory=PATH_TO_FRONTEND_STATIC, html=True), name="static_frontend")
else:
    print(f"Warning: Frontend static directory not found at {PATH_TO_FRONTEND_STATIC}")
    @app.get("/")
    async def root_placeholder():
        return {"message": "MindMap WebSocket Server is running. Frontend not found."}


if __name__ == "__main__":
    # This block is for when you run the script directly (e.g., python websocket_server.py)
    # We will programmatically start Uvicorn here to ensure the event loop policy is set.
    # No longer strictly necessary to set WindowsSelectorEventLoopPolicy if using Popen in a thread
    # if sys.platform == "win32":
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    import uvicorn
    uvicorn.run(
        "websocket_server:app", # app_module:app_instance_name
        host="0.0.0.0",
        port=8000,
        reload=True # Enable reloader
    )
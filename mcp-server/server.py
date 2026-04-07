import os
import json
import subprocess
import sys
from mcp.server.fastmcp import FastMCP

# 1. Check socket
nvim_socket = os.environ.get("NVIM_LISTEN_ADDRESS")
if not nvim_socket:
    raise RuntimeError("NVIM_LISTEN_ADDRESS environment variable is required")

app = FastMCP("cade-nvim-mcp")

def run_nvim_script(script: str) -> str:
    """Runs a python script in a separate process that connects to nvim."""
    cmd = [
        sys.executable, "-c",
        f"import pynvim, sys, os\n"
        f"try:\n"
        f"    nvim = pynvim.attach('socket', path='{nvim_socket}')\n"
        f"except Exception as e:\n"
        f"    print('DRY_RUN_SKIPPED: Could not connect to Neovim socket.')\n"
        f"    sys.exit(0)\n"
        f"{script}\n"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"Error: {result.stderr}"
    return result.stdout.strip()

@app.resource("ide://active-editor/buffer")
def read_buffer() -> str:
    """Read the current active buffer contents from Neovim"""
    script = (
        "buf = nvim.current.buffer\n"
        "print('\\n'.join(buf[:]))"
    )
    return run_nvim_script(script)

@app.tool()
def ide_read_buffer() -> str:
    """Reads the entire content of the currently active Neovim buffer and returns it as a string along with the file path."""
    script = (
        "buf = nvim.current.buffer\n"
        "name = buf.name or 'Unnamed Buffer'\n"
        "cursor = nvim.current.window.cursor\n"
        "text = '\\n'.join(buf[:])\n"
        "print(f'--- Active Neovim Buffer: {name} (Cursor: Line {cursor[0]}, Col {cursor[1]}) ---\\n{text}\\n--- End of Buffer ---')\n"
    )
    return run_nvim_script(script)

@app.tool()
def ide_propose_edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replaces exact text in the currently active Neovim buffer without saving to disk."""
    # We use json to safely escape strings for the python script payload
    safe_path = json.dumps(path)
    safe_old = json.dumps(old_string)
    safe_new = json.dumps(new_string)
    safe_replace_all = "True" if replace_all else "False"
    
    script = (
        "import os\n"
        "buf = nvim.current.buffer\n"
        "if not buf.name:\n"
        "    print('DRY_RUN_SKIPPED: Active buffer has no name.')\n"
        "    sys.exit(0)\n"
        f"if os.path.abspath(buf.name) != os.path.abspath({safe_path}):\n"
        "    print(f'DRY_RUN_SKIPPED: Active buffer is {buf.name}, not ' + " + safe_path + ")\n"
        "    sys.exit(0)\n"
        "text = '\\n'.join(buf[:])\n"
        f"if {safe_old} not in text:\n"
        "    print('Error: old_string not found in the active buffer.')\n"
        "    sys.exit(0)\n"
        f"if {safe_replace_all}:\n"
        f"    new_text = text.replace({safe_old}, {safe_new})\n"
        "else:\n"
        f"    new_text = text.replace({safe_old}, {safe_new}, 1)\n"
        "buf[:] = new_text.split('\\n')\n"
        "print('Edit applied successfully to the unsaved Neovim buffer (dry-run intercepted by cade-nvim).')\n"
    )
    return run_nvim_script(script)

@app.tool()
def ide_apply_patch(patch: str) -> str:
    """Applies a unified diff patch to the active Neovim buffer."""
    safe_patch = json.dumps(patch)
    script = (
        "import os, tempfile, subprocess\n"
        "buf = nvim.current.buffer\n"
        "if not buf.name:\n"
        "    print('DRY_RUN_SKIPPED: Active buffer has no name.')\n"
        "    sys.exit(0)\n"
        # Since patches usually specify file paths, we need to ensure the patch applies to the current file.
        # However, a patch might have headers `--- a/...` `+++ b/...`.
        # For simplicity, we write the buffer to a temp file and run `patch -p1` or similar, but
        # `patch` command might be tricky if the header paths don't match the temp file.
        # Alternatively, we can use `patch` on the exact `buf.name` file path if we assume the patch targets it,
        # but that modifies the disk, which defeats the purpose.
        # Wait, if we use `patch < temp.patch` with `buf.name` as target... NO, we want to modify the unsaved buffer!
        # Instead, let's write buffer to `temp.txt`, and modify the patch header to point to `temp.txt`?
        # Or we can just use `patch` with `-i temp.patch -o temp_out.txt` and then read `temp_out.txt` back!
        # If the patch doesn't supply exactly the right filename, `patch` can be fed from stdin or with `-u`.
        # `patch -u - tf` applies to `tf`.
        "with tempfile.NamedTemporaryFile('w', delete=False) as f:\n"
        "    f.write('\\n'.join(buf[:]) + '\\n')\n"
        "    tf_name = f.name\n"
        "with tempfile.NamedTemporaryFile('w', delete=False) as f_patch:\n"
        f"    f_patch.write({safe_patch})\n"
        "    f_patch_name = f_patch.name\n"
        "try:\n"
        "    res = subprocess.run(['patch', '-u', tf_name, '-i', f_patch_name], capture_output=True, text=True)\n"
        "    if res.returncode == 0:\n"
        "        with open(tf_name, 'r') as f:\n"
        "            new_text = f.read()\n"
        "        buf[:] = new_text.splitlines()\n"
        "        print('Patch applied successfully to the unsaved Neovim buffer (dry-run intercepted by cade-nvim).')\n"
        "    else:\n"
        "        # If the patch failed, it's possible the patch targeted the wrong file path, or the buffer is too different.\n"
        "        # But if the file path in the patch doesn't match the current file, we should SKIP.\n"
        f"        patch_str = {safe_patch}\n"
        "        target_file = os.path.basename(buf.name)\n"
        "        if target_file not in patch_str:\n"
        "            print(f'DRY_RUN_SKIPPED: Patch does not seem to target active buffer ({target_file}).')\n"
        "        else:\n"
        "            print(f'Error applying patch to active buffer: {res.stderr}\\n{res.stdout}')\n"
        "finally:\n"
        "    os.remove(tf_name)\n"
        "    os.remove(f_patch_name)\n"
    )
    return run_nvim_script(script)

if __name__ == "__main__":
    app.run()

#!/usr/bin/env bash
set -e

# Find the absolute directory of the script, regardless of where it's called from
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVER_DIR="$DIR/mcp-server"

echo "Building CADE-nvim..."
cd "$SERVER_DIR"

# 1. Set up the Python virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# 2. Install required MCP dependencies
echo "Installing Python dependencies (mcp, pynvim)..."
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install mcp pynvim --quiet

# 3. Automatically register the MCP server in CADE's settings.json
echo "Registering cade-nvim with CADE..."
./venv/bin/python << 'EOF'
import os
import json
import sys

settings_path = os.path.expanduser("~/.cade/settings.json")
if not os.path.exists(settings_path):
    print("WARNING: CADE settings.json not found. You may need to manually configure the MCP server.")
    sys.exit(0)

try:
    with open(settings_path, 'r') as f:
        data = json.load(f)
except Exception as e:
    print(f"WARNING: Could not parse {settings_path}: {e}")
    sys.exit(0)

if "mcpServers" not in data:
    data["mcpServers"] = {}

server_dir = os.environ.get("PWD")
data["mcpServers"]["cade-nvim"] = {
    "command": os.path.join(server_dir, "venv/bin/python"),
    "args": [os.path.join(server_dir, "server.py")],
    "env": {
        "NVIM_LISTEN_ADDRESS": "/tmp/nvim.pipe"
    },
    "disabled": False
}

try:
    with open(settings_path, 'w') as f:
        json.dump(data, f, indent=2)
    print("Successfully injected cade-nvim into CADE MCP configurations!")
except Exception as e:
    print(f"WARNING: Could not write to {settings_path}: {e}")
EOF

echo "CADE-nvim installation complete!"

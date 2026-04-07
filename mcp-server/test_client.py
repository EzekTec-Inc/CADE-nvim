import asyncio
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from mcp import StdioServerParameters as ServerParameters

async def main():
    server_params = ServerParameters(
        command="/home/engr-uba/Downloads/02 Rust-project/CADE-nvim/mcp-server/venv/bin/python",
        args=["/home/engr-uba/Downloads/02 Rust-project/CADE-nvim/mcp-server/server.py"],
        env={"NVIM_LISTEN_ADDRESS": "/tmp/nvim.pipe"}
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("ide_propose_edit", arguments={
                "old_string": "do you see this text?",
                "new_string": "The Phase 2 dry-run is working perfectly!"
            })
            print(result.content[0].text)

asyncio.run(main())

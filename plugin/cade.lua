-- CADE-nvim Initialization
-- This file is automatically loaded by Neovim when the plugin is installed.

if vim.g.loaded_cade_nvim == 1 then
  return
end
vim.g.loaded_cade_nvim = 1

local socket_path = "/tmp/nvim.pipe"

-- Automatically set the environment variable globally for Neovim and all child processes
if vim.env.NVIM_LISTEN_ADDRESS == nil or vim.env.NVIM_LISTEN_ADDRESS == "" then
  vim.env.NVIM_LISTEN_ADDRESS = socket_path
end

-- Safely start the internal server on the socket
pcall(function()
  vim.fn.serverstart(socket_path)
end)

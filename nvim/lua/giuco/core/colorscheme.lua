local status, _ = pcall(vim.cmd, "colorscheme nightfly")

if not status then
    print("colors scheme not found")
    return
end


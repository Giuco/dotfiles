#!/usr/bin/env bash
# Symlink dotfiles into place. Safe to re-run (ln -sfn overwrites).
# -n: treat an existing symlink-to-dir as a file so it's replaced, not
#     dereferenced (otherwise a self-referential link is created inside it).

mkdir -p ~/.config ~/.config/zed ~/.config/ghostty ~/.claude

# Generate zed/settings.json from base + local + secrets before linking.
~/dotfiles/zed/build.sh

ln -sfn ~/dotfiles/.zshrc            ~/.zshrc
ln -sfn ~/dotfiles/.ideavimrc        ~/.ideavimrc
ln -sfn ~/dotfiles/starship.toml     ~/.config/starship.toml
ln -sfn ~/dotfiles/nvim              ~/.config/nvim
ln -sfn ~/dotfiles/karabiner         ~/.config/karabiner
ln -sfn ~/dotfiles/zed/keymap.json   ~/.config/zed/keymap.json
ln -sfn ~/dotfiles/zed/settings.json ~/.config/zed/settings.json
ln -sfn ~/dotfiles/ghostty/config    ~/.config/ghostty/config
ln -sfn ~/dotfiles/claude/settings.json ~/.claude/settings.json

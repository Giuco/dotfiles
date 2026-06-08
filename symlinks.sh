#!/usr/bin/env bash
# Symlink dotfiles into place. Safe to re-run (ln -sf overwrites).

mkdir -p ~/.config ~/.config/zed ~/.config/ghostty ~/.claude

# Generate zed/settings.json from base + local + secrets before linking.
~/dotfiles/zed/build.sh

ln -sf ~/dotfiles/.zshrc            ~/.zshrc
ln -sf ~/dotfiles/.ideavimrc        ~/.ideavimrc
ln -sf ~/dotfiles/starship.toml     ~/.config/starship.toml
ln -sf ~/dotfiles/nvim              ~/.config/nvim
ln -sf ~/dotfiles/karabiner         ~/.config/karabiner
ln -sf ~/dotfiles/zed/keymap.json   ~/.config/zed/keymap.json
ln -sf ~/dotfiles/zed/settings.json ~/.config/zed/settings.json
ln -sf ~/dotfiles/ghostty/config    ~/.config/ghostty/config
ln -sf ~/dotfiles/claude/settings.json ~/.claude/settings.json

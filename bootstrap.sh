#!/usr/bin/env bash
# Fresh-machine bootstrap. Idempotent — safe to re-run.
#
# Usage:
#   bash ~/dotfiles/bootstrap.sh
#
# Performs, in order:
#   1. Xcode Command Line Tools
#   2. Homebrew (handles Apple Silicon path)
#   3. brew bundle (Brewfile)
#   4. Oh My Zsh
#   5. Custom OMZ plugins
#   6. Symlinks
#   7. Manual follow-ups

set -euo pipefail

DOTFILES="$HOME/dotfiles"
step() { printf '\n\033[1;34m==> Step %s: %s\033[0m\n' "$1" "$2"; }

# 1. Xcode Command Line Tools -------------------------------------------------
step 1 "Xcode Command Line Tools"
if xcode-select -p >/dev/null 2>&1; then
  echo "Already installed."
else
  xcode-select --install
  echo "Accept the GUI prompt, wait for install to finish, then re-run this script."
  exit 1
fi

# 2. Homebrew -----------------------------------------------------------------
step 2 "Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
# Make brew available in this shell for the rest of the script
if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"   # Apple Silicon
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"      # Intel
fi

# 3. Brewfile -----------------------------------------------------------------
step 3 "brew bundle"
brew bundle install --file "$DOTFILES/Brewfile"

# 4. Oh My Zsh ----------------------------------------------------------------
step 4 "Oh My Zsh"
if [ -d "$HOME/.oh-my-zsh" ]; then
  echo "Already installed."
else
  RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi

# 5. Custom OMZ plugins -------------------------------------------------------
step 5 "Custom zsh plugins"
ZSH_PLUGINS="$HOME/.oh-my-zsh/custom/plugins"
clone_plugin() {
  local repo="$1" name="$2"
  if [ -d "$ZSH_PLUGINS/$name" ]; then
    echo "  $name: already installed"
  else
    git clone --depth=1 "$repo" "$ZSH_PLUGINS/$name"
  fi
}
clone_plugin https://github.com/zsh-users/zsh-autosuggestions     zsh-autosuggestions
clone_plugin https://github.com/zsh-users/zsh-syntax-highlighting zsh-syntax-highlighting
clone_plugin https://github.com/jeffreytse/zsh-vi-mode            zsh-vi-mode

# 6. Symlinks -----------------------------------------------------------------
step 6 "Symlinks"
bash "$DOTFILES/symlinks.sh"

# 7. Manual follow-ups --------------------------------------------------------
step 7 "Manual follow-ups"
cat <<'EOF'

Bootstrap complete. A few things to finish by hand:

  - Open a new terminal so the new .zshrc is loaded.
  - gh auth login                          (GitHub CLI auth)
  - Launch Karabiner-Elements once         (grants accessibility permission)
  - Sign into App Store apps               (Spotify, Pocket Casts, etc.)
  - Set up SSH keys                        (ssh-keygen + add to GitHub)
  - Set up .gitconfig                      (user.name, user.email, signing key)

EOF

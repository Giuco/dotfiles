# Oh My Zsh
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git gh zsh-autosuggestions zsh-vi-mode zsh-syntax-highlighting)

# zsh-vi-mode cursor shapes per mode (must be set before plugin loads)
ZVM_NORMAL_MODE_CURSOR=$ZVM_CURSOR_BLOCK
ZVM_INSERT_MODE_CURSOR=$ZVM_CURSOR_BEAM
ZVM_VISUAL_MODE_CURSOR=$ZVM_CURSOR_UNDERLINE
ZVM_VISUAL_LINE_MODE_CURSOR=$ZVM_CURSOR_UNDERLINE

source $ZSH/oh-my-zsh.sh

# Prompt
eval "$(starship init zsh)"

# fzf
eval "$(fzf --zsh)"
export FZF_DEFAULT_COMMAND="fd --hidden --strip-cwd-prefix --exclude .git"
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND="fd --type=d --hidden --strip-cwd-prefix --exclude .git"
_fzf_compgen_path() { fd --hidden --exclude .git . "$1" }
_fzf_compgen_dir()  { fd --type=d --hidden --exclude .git . "$1" }

# fzf theme
fg="#CBE0F0"
bg="#011628"
bg_highlight="#143652"
purple="#B388FF"
blue="#06BCE4"
cyan="#2CF9ED"
export FZF_DEFAULT_OPTS="--color=fg:${fg},bg:${bg},hl:${purple},fg+:${fg},bg+:${bg_highlight},hl+:${purple},info:${blue},prompt:${cyan},pointer:${cyan},marker:${cyan},spinner:${cyan},header:${cyan}"

# bat
export BAT_THEME="Catppuccin Mocha"

# thefuck
eval $(thefuck --alias)

# zoxide (replaces z plugin)
eval "$(zoxide init zsh)"

# vi mode handled by zsh-vi-mode plugin (see plugins list above)
export KEYTIMEOUT=1

# zsh-vi-mode resets keybindings after init, so rebind anything custom here
function zvm_after_init() {
  bindkey '^[^?' backward-kill-word  # Option+Backspace deletes whole word
  eval "$(fzf --zsh)"                # re-apply fzf bindings (^R/^T/Alt-C) that zvm clobbers
}

# Aliases
source ~/dotfiles/alias.sh

# Local tooling PATHs
export PATH="$HOME/.codeium/windsurf/bin:$PATH"   # Windsurf
# dbt (Fusion + installer)
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
alias dbtf="$HOME/.local/bin/dbt"

# Machine-specific overrides & secrets (not tracked in git)
[ -f ~/.zshrc.local ] && source ~/.zshrc.local

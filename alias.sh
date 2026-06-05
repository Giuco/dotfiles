# eza (left `ls` untouched on purpose — many tools rely on POSIX `ls` output)
alias l="eza -l --icons --color=always --header --git --created --changed --no-user --no-permissions --sort modified --all --binary"
alias ll="eza --color=always --long --git --icons=always"
alias la="eza --color=always --long --git --icons=always --all"
alias tree="eza --tree --icons=always"

# editor
alias vim="nvim"
alias v="vim"

# navigation
alias cd="z"

# kubernetes / docker
alias kc="kubectl"
alias dc="docker compose"

# python
alias python="python3"

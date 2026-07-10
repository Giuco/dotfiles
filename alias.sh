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
# alias grep="rg"
# alias find="fd"

# github
# gh_mine: GitHub notifications that actually need me — direct @mentions, direct
# review requests (not team-routed), and new activity on threads I'm in, each with
# a clickable link. Notifications stay unread after a PR merges, so review requests
# are gated on the PR still being open and still listing me in requested_reviewers
# (the API uses one "review_requested" reason for both direct and team requests).
# subject.url is the API URL; rewrite it to the browser URL. Needs gh (jq via --jq).
gh_mine() {
  local me; me=$(gh api /user --jq .login)
  gh api "/notifications?participating=true" --paginate \
    --jq '.[] | select(.reason=="mention" or .reason=="assign" or .reason=="comment" or .reason=="review_requested")
          | [.reason, .repository.full_name, .subject.type, .subject.title, .subject.url,
             ((.subject.url // "") | sub("^https://api.github.com/repos/"; "https://github.com/") | sub("/pulls/"; "/pull/"))] | @tsv' \
  | while IFS=$'\t' read -r reason repo type title apiurl link; do
      if [ "$reason" = "review_requested" ]; then
        # keep only PRs still open and still listing me personally as a reviewer;
        # drops merged/closed PRs and team-routed requests. The whole test runs in
        # jq (no shell locals) to sidestep a zsh quirk with `local` in a piped loop.
        [ "$type" = "PullRequest" ] && [ -n "$apiurl" ] || continue
        me="$me" gh api "$apiurl" \
          --jq 'select(.state=="open" and ([.requested_reviewers[]?.login] | index(env.me))) | .number' \
          2>/dev/null | grep -q . || continue
      fi
      printf '%s\t%s\t%s\t%s\n' "$reason" "$repo" "$title" "$link"
    done
}

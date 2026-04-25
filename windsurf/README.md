# Cascade allow-list manager

Declarative manager for the Windsurf / Cascade terminal allow list. The intended state lives in `cascade_allowlist.toml`; running `apply` makes the on-disk `user_settings.pb` match it. Idempotent.

## Quickstart

```bash
# Show the desired list
./cascade_allowlist.py show

# Sanity-check it
./cascade_allowlist.py lint

# Preview what would change vs the live pb
./cascade_allowlist.py diff

# Apply (Windsurf must be quit first)
./cascade_allowlist.py apply
```

First run will create a venv at `~/.local/share/cascade-allowlist/.venv` and install [`blackboxprotobuf`](https://pypi.org/project/blackboxprotobuf/) into it, then re-exec.

## Editing the list

Open `cascade_allowlist.toml`. Each `[categories."<name>"]` table contributes entries to the final list, in the order the tables appear. A category supports either or both keys:

```toml
[categories."git.readonly"]
entries = [
    "git status *",
    "git log *",
    # ...
]

[categories."dbt.readonly".cross]
prefixes    = ["dbt", "~/.local/bin/dbt"]
subcommands = ["--version", "parse", "ls *", "test *"]
```

Conventions:

- Trailing ` *` means **prefix match** (any args allowed). Example: `git status *`.
- No trailing ` *` means **exact match**. Example: `git stash`.
- `cross` builds the Cartesian product of `prefixes` × `subcommands`.

After editing, run `lint` (warns about duplicates and entries shadowed by a wildcard sibling), then `diff`, then `apply`.

## Safety model

- `apply` refuses to write while a process matching `--process-pattern` (default `Windsurf.app`) is running, because Windsurf rewrites `user_settings.pb` on quit.
- Two timestamped backups are made before each write:
  - next to the original (`user_settings.pb.bak-<ts>`)
  - in `--backup-dir` (default `~/.local/state/cascade-allowlist/backups`)
- The pb is decoded, mutated, re-encoded, decoded again, and verified to round-trip semantically before any overwrite.
- Writes are atomic (`tmp` + `os.replace`).
- Each `apply` writes a `.log` file in the backup dir capturing sizes, SHA-256s, removed entries, added entries, and backup paths.

## Recovery

If something looks wrong:

```bash
# Quit Windsurf first
cp ~/.local/state/cascade-allowlist/backups/user_settings.pb.bak-<ts> \
   ~/.codeium/windsurf/user_settings.pb
```

(or use the backup next to the original at `~/.codeium/windsurf/user_settings.pb.bak-<ts>`).

## Configuration overrides

| Aspect | Flag | Env var | Default |
| --- | --- | --- | --- |
| TOML config | `--config` | `CASCADE_ALLOWLIST_CONFIG` | `<script-dir>/cascade_allowlist.toml` |
| pb path | `--pb-path` | `CASCADE_PB_PATH` | `~/.codeium/windsurf/user_settings.pb` |
| Allow-list field number | `--field` | `CASCADE_ALLOWLIST_FIELD` | `85` (auto-discovered if invalid) |
| Backup dir | `--backup-dir` | `CASCADE_BACKUP_DIR` | `~/.local/state/cascade-allowlist/backups` |
| Process pattern | `--process-pattern` | `CASCADE_PROCESS` | `Windsurf.app` |
| Venv dir | — | `CASCADE_VENV_DIR` | `~/.local/share/cascade-allowlist/.venv` |
| Skip bootstrap | — | `CASCADE_SKIP_BOOTSTRAP=1` | off |

The script auto-discovers the protobuf field holding the allow list if the configured field number doesn't look right (Windsurf may renumber across major versions).

## Notes

- Requires Python ≥ 3.11 (uses stdlib `tomllib`).
- macOS-tested. On Linux, override `--pb-path` and `--process-pattern`.
- The `.proto` schema is not shipped with Windsurf, so the script uses `blackboxprotobuf` (schemaless TLV round-tripping). It refuses to write if the untouched file fails a semantic round-trip.

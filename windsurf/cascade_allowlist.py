#!/usr/bin/env python3
"""Declarative manager for the Cascade (Windsurf) terminal allow list.

The intended allow list is read from a TOML config (default:
``cascade_allowlist.toml`` next to this script). Running ``apply`` sets the
on-disk ``user_settings.pb`` to exactly that list. Idempotent.

Subcommands:
    show     print the effective DESIRED list
    diff     dry-run: show add/remove diff vs current pb (default)
    lint     sanity-check DESIRED for duplicates / shadowed entries
    apply    write the new pb (Windsurf must be quit)

Overrides (flag or env var):
    --config            CASCADE_ALLOWLIST_CONFIG default: <script-dir>/cascade_allowlist.toml
    --pb-path           CASCADE_PB_PATH         default: ~/.codeium/windsurf/user_settings.pb
    --field             CASCADE_ALLOWLIST_FIELD default: 85 (auto-discovered if invalid)
    --backup-dir        CASCADE_BACKUP_DIR      default: ~/.local/state/cascade-allowlist/backups
    --process-pattern   CASCADE_PROCESS         default: Windsurf.app

First run will create a venv at ``~/.local/share/cascade-allowlist/.venv``
and ``pip install blackboxprotobuf`` into it, then re-exec.  Set
``CASCADE_SKIP_BOOTSTRAP=1`` to skip and use the current interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import platform
import subprocess
import sys
import time
from dataclasses import dataclass

if sys.version_info < (3, 11):
    sys.exit("cascade_allowlist requires Python >= 3.11 (tomllib in stdlib)")
import tomllib  # noqa: E402

# ---------------------------------------------------------------------------
# Bootstrap: ensure ``blackboxprotobuf`` is importable. Done before any heavy
# imports / argument parsing so the re-exec is cheap.
# ---------------------------------------------------------------------------

VENV_DIR = pathlib.Path(
    os.environ.get("CASCADE_VENV_DIR",
                   pathlib.Path.home() / ".local" / "share" / "cascade-allowlist" / ".venv")
).expanduser()


def _venv_python() -> pathlib.Path:
    return VENV_DIR / "bin" / "python"


def _bootstrap() -> None:
    """Create venv + install deps, then re-exec into it if needed."""
    if os.environ.get("CASCADE_SKIP_BOOTSTRAP") == "1":
        return
    try:
        import blackboxprotobuf  # noqa: F401
        return
    except ImportError:
        pass

    venv_py = _venv_python()
    if not venv_py.exists():
        print(f"[bootstrap] creating venv at {VENV_DIR}", file=sys.stderr)
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
            subprocess.check_call([
                str(venv_py), "-m", "pip", "install", "--quiet",
                "--disable-pip-version-check", "blackboxprotobuf",
            ])
        except subprocess.CalledProcessError as e:
            sys.exit(
                f"[bootstrap] failed: {e}\n"
                f"manual fallback: pipx install blackboxprotobuf\n"
                f"then re-run with CASCADE_SKIP_BOOTSTRAP=1"
            )

    # Compare prefixes (not resolved paths) — venv python is a symlink chain
    # that resolves back to the system interpreter; sys.prefix is what differs.
    if pathlib.Path(sys.prefix).resolve() != VENV_DIR.resolve():
        os.execv(str(venv_py), [str(venv_py), str(pathlib.Path(__file__).resolve()), *sys.argv[1:]])


_bootstrap()
import blackboxprotobuf  # noqa: E402


# ---------------------------------------------------------------------------
# Config loader (TOML)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = pathlib.Path(__file__).parent / "cascade_allowlist.toml"


def _expand_category(name: str, body: dict) -> list[str]:
    """Expand a single TOML [categories.<name>] table into a list of strings.

    Supports two keys (either or both):
        entries = [...]
        cross   = { prefixes = [...], subcommands = [...] }
    """
    out: list[str] = []
    if "entries" in body:
        if not isinstance(body["entries"], list) or not all(isinstance(e, str) for e in body["entries"]):
            sys.exit(f"!! [{name}].entries must be a list of strings")
        out.extend(body["entries"])
    if "cross" in body:
        cx = body["cross"]
        try:
            prefixes = cx["prefixes"]; subcommands = cx["subcommands"]
        except (KeyError, TypeError):
            sys.exit(f"!! [{name}].cross must be a table with 'prefixes' and 'subcommands' lists")
        if not (isinstance(prefixes, list) and isinstance(subcommands, list)):
            sys.exit(f"!! [{name}].cross.prefixes and .subcommands must be lists")
        out.extend(f"{p} {s}" for p in prefixes for s in subcommands)
    extras = set(body) - {"entries", "cross"}
    if extras:
        print(f"[warn] unknown keys in [{name}]: {sorted(extras)}", file=sys.stderr)
    return out


def load_allowlist(path: pathlib.Path) -> dict[str, list[str]]:
    """Parse the TOML file and return an ordered category -> entries dict."""
    if not path.exists():
        sys.exit(f"!! config not found: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)
    cats = data.get("categories")
    if not isinstance(cats, dict) or not cats:
        sys.exit(f"!! {path}: missing or empty [categories.*] tables")
    return {name: _expand_category(name, body) for name, body in cats.items()}


def desired_list(allowlist: dict[str, list[str]]) -> list[str]:
    """Flatten the categorized allow list into the ordered on-disk list."""
    out: list[str] = []
    for entries in allowlist.values():
        out.extend(entries)
    return out


# ---------------------------------------------------------------------------
# pb I/O
# ---------------------------------------------------------------------------

DEFAULT_PB_PATH = "~/.codeium/windsurf/user_settings.pb"
DEFAULT_FIELD = "85"
DEFAULT_BACKUP_DIR = "~/.local/state/cascade-allowlist/backups"
DEFAULT_PROCESS = "Windsurf.app"


@dataclass
class Config:
    pb_path: pathlib.Path
    field: str
    backup_dir: pathlib.Path
    process_pattern: str
    config_path: pathlib.Path
    allowlist: dict[str, list[str]]


def load_config(args: argparse.Namespace) -> Config:
    pb = pathlib.Path(args.pb_path or os.environ.get("CASCADE_PB_PATH") or DEFAULT_PB_PATH).expanduser()
    field = args.field or os.environ.get("CASCADE_ALLOWLIST_FIELD") or DEFAULT_FIELD
    backup = pathlib.Path(args.backup_dir or os.environ.get("CASCADE_BACKUP_DIR") or DEFAULT_BACKUP_DIR).expanduser()
    proc = args.process_pattern or os.environ.get("CASCADE_PROCESS") or DEFAULT_PROCESS
    cfg_path = pathlib.Path(
        args.config or os.environ.get("CASCADE_ALLOWLIST_CONFIG") or DEFAULT_CONFIG_PATH
    ).expanduser()
    allowlist = load_allowlist(cfg_path)
    return Config(pb_path=pb, field=field, backup_dir=backup, process_pattern=proc,
                  config_path=cfg_path, allowlist=allowlist)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def process_running(pattern: str) -> bool:
    r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    return bool(r.stdout.strip())


def _is_string_list(v) -> bool:
    return isinstance(v, list) and v and all(isinstance(x, (str, bytes, bytearray)) for x in v)


def _to_str_list(v) -> list[str]:
    return [bytes(e).decode("utf-8") if isinstance(e, (bytes, bytearray)) else e for e in v]


def _looks_like_allowlist(entries: list[str]) -> int:
    """Heuristic score: count entries that look like shell command patterns."""
    score = 0
    common = ("git ", "dbt", "ls", "cat", "echo", "grep", "find", "which",
              "databricks", "gh ", "head", "tail", "rg ", "sed ", "awk ",
              "python", "node", "npm")
    for e in entries:
        if any(e.startswith(c) or c.strip() == e for c in common):
            score += 1
    return score


def resolve_field(msg: dict, requested: str) -> str:
    """Validate ``requested`` field; if it doesn't look like the allow list,
    auto-discover the best top-level repeated-string field."""
    candidates: list[tuple[str, list[str], int]] = []
    for k, v in msg.items():
        if _is_string_list(v):
            entries = _to_str_list(v)
            candidates.append((k, entries, _looks_like_allowlist(entries)))
    if not candidates:
        sys.exit("!! No top-level repeated-string field found in pb")

    if requested in msg and _is_string_list(msg[requested]):
        entries = _to_str_list(msg[requested])
        score = _looks_like_allowlist(entries)
        if score >= max(3, len(entries) // 4):
            return requested
        # Requested field exists but doesn't look right; warn + fall through
        print(f"[warn] field {requested!r} present but doesn't look like the allow list "
              f"(score={score}, len={len(entries)}); auto-discovering",
              file=sys.stderr)

    # Pick highest-scoring candidate (ties: longest list wins)
    candidates.sort(key=lambda c: (c[2], len(c[1])), reverse=True)
    best, _, score = candidates[0]
    if score == 0:
        sys.exit("!! Could not auto-discover allow-list field; pass --field explicitly")
    if best != requested:
        print(f"[info] auto-discovered allow-list field: {best!r} (was --field={requested!r})",
              file=sys.stderr)
    return best


@dataclass
class PbState:
    raw: bytes
    msg: dict
    typedef: dict
    field: str
    entries: list[str]


def load_pb(cfg: Config) -> PbState:
    if not cfg.pb_path.exists():
        sys.exit(f"!! pb not found: {cfg.pb_path}")
    raw = cfg.pb_path.read_bytes()
    msg, typedef = blackboxprotobuf.decode_message(raw)

    # Untouched round-trip sanity (semantic check is sufficient)
    rt = blackboxprotobuf.encode_message(msg, typedef)
    if rt != raw:
        msg_rt, _ = blackboxprotobuf.decode_message(rt)
        if msg_rt != msg:
            sys.exit("!! Untouched round-trip semantic mismatch. Aborting.")

    field = resolve_field(msg, cfg.field)
    return PbState(raw=raw, msg=msg, typedef=typedef, field=field, entries=_to_str_list(msg[field]))


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

def lint_desired(desired: list[str]) -> list[str]:
    warnings: list[str] = []

    seen: set[str] = set()
    for e in desired:
        if e in seen:
            warnings.append(f"duplicate entry: {e!r}")
        seen.add(e)

    wildcards = {e[:-2] for e in desired if e.endswith(" *")}
    for e in desired:
        if e.endswith(" *"):
            continue
        parts = e.split(" ")
        for i in range(1, len(parts) + 1):
            prefix = " ".join(parts[:i])
            if prefix in wildcards and prefix != e:
                warnings.append(f"shadowed by {prefix + ' *'!r}: {e!r}")
                break
    return warnings


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_show(_args, cfg: Config) -> int:
    desired = desired_list(cfg.allowlist)
    print(f"# Desired allow list ({len(desired)} entries) — from {cfg.config_path}")
    for category, entries in cfg.allowlist.items():
        print(f"\n## {category} ({len(entries)})")
        for e in entries:
            print(f"  {e}")
    return 0


def cmd_lint(_args, cfg: Config) -> int:
    desired = desired_list(cfg.allowlist)
    warnings = lint_desired(desired)
    if not warnings:
        print(f"lint OK ({len(desired)} entries)")
        return 0
    print(f"lint: {len(warnings)} warning(s):")
    for w in warnings:
        print(f"  - {w}")
    return 1


def print_diff(current: list[str], desired: list[str]) -> tuple[list[str], list[str]]:
    cur_set, des_set = set(current), set(desired)
    removed = [e for e in current if e not in des_set]
    added = [e for e in desired if e not in cur_set]
    print(f"Current: {len(current)}  →  Desired: {len(desired)}")
    print(f"\nWill REMOVE ({len(removed)}):")
    for e in removed: print(f"  - {e}")
    print(f"\nWill ADD ({len(added)}):")
    for e in added: print(f"  + {e}")
    if current == desired:
        print("\nNo changes needed.")
    return removed, added


def cmd_diff(_args, cfg: Config) -> int:
    st = load_pb(cfg)
    print(f"config: {cfg.config_path}")
    print(f"pb:     {cfg.pb_path}")
    print(f"size:   {len(st.raw)}B sha={sha(st.raw)}")
    print(f"field:  {st.field}\n")
    print_diff(st.entries, desired_list(cfg.allowlist))
    return 0


def cmd_apply(args, cfg: Config) -> int:
    desired = desired_list(cfg.allowlist)
    warnings = lint_desired(desired)
    if warnings and not args.force:
        print(f"lint: {len(warnings)} warning(s). Re-run with --force to override.")
        for w in warnings: print(f"  - {w}")
        return 1

    if platform.system() != "Darwin":
        print(f"[warn] not running on macOS ({platform.system()}); paths and process pattern may need overrides",
              file=sys.stderr)

    st = load_pb(cfg)
    print(f"config: {cfg.config_path}")
    print(f"pb:     {cfg.pb_path}")
    print(f"size:   {len(st.raw)}B sha={sha(st.raw)}")
    print(f"field:  {st.field}\n")
    removed, added = print_diff(st.entries, desired)
    if st.entries == desired:
        return 0

    st.msg[st.field] = [e.encode("utf-8") for e in desired]
    new_bytes = blackboxprotobuf.encode_message(st.msg, st.typedef)
    msg2, _ = blackboxprotobuf.decode_message(new_bytes)
    if _to_str_list(msg2[st.field]) != desired:
        sys.exit("!! Post-encode verification FAILED")
    if set(msg2.keys()) != set(st.msg.keys()):
        sys.exit("!! Top-level keys drifted")
    print(f"\nNew pb: {len(new_bytes)}B sha={sha(new_bytes)}  [verify OK]")

    if args.dry_run:
        print("\n--dry-run: not writing.")
        return 0

    if process_running(cfg.process_pattern):
        sys.exit(f"!! process matching {cfg.process_pattern!r} is running — quit it before --apply")

    cfg.backup_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak1 = cfg.pb_path.parent / f"{cfg.pb_path.name}.bak-{ts}"
    bak2 = cfg.backup_dir / f"{cfg.pb_path.name}.bak-{ts}"
    bak1.write_bytes(st.raw); bak2.write_bytes(st.raw)

    tmp = cfg.pb_path.with_suffix(cfg.pb_path.suffix + ".new")
    tmp.write_bytes(new_bytes)
    os.replace(tmp, cfg.pb_path)

    log = cfg.backup_dir / f"allowlist-edit-{ts}.log"
    log.write_text(
        f"pb_path={cfg.pb_path}\n"
        f"field={st.field}\n"
        f"original_size={len(st.raw)} sha={sha(st.raw)}\n"
        f"new_size={len(new_bytes)} sha={sha(new_bytes)}\n"
        f"removed={removed}\n"
        f"added={added}\n"
        f"backups={bak1},{bak2}\n"
    )
    print(f"\nWROTE {cfg.pb_path} ({len(new_bytes)}B)")
    print(f"Backups: {bak1}\n         {bak2}")
    print(f"Log:     {log}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="path to TOML allow-list config (env: CASCADE_ALLOWLIST_CONFIG)")
    p.add_argument("--pb-path", help="path to user_settings.pb (env: CASCADE_PB_PATH)")
    p.add_argument("--field", help="protobuf field number for allow list (env: CASCADE_ALLOWLIST_FIELD)")
    p.add_argument("--backup-dir", help="dir for off-tree backups + logs (env: CASCADE_BACKUP_DIR)")
    p.add_argument("--process-pattern", help="pgrep pattern for the running editor (env: CASCADE_PROCESS)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cascade_allowlist",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("show", help="print DESIRED");           _add_common(s); s.set_defaults(func=cmd_show)
    s = sub.add_parser("lint", help="sanity-check DESIRED");    _add_common(s); s.set_defaults(func=cmd_lint)
    s = sub.add_parser("diff", help="show diff vs current pb"); _add_common(s); s.set_defaults(func=cmd_diff)
    s = sub.add_parser("apply", help="write new pb")
    _add_common(s)
    s.add_argument("--dry-run", action="store_true", help="compute new bytes but do not write")
    s.add_argument("--force", action="store_true", help="ignore lint warnings")
    s.set_defaults(func=cmd_apply)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        # Default to diff, populating the common args defaults
        args = parser.parse_args(["diff", *(argv or [])])
    cfg = load_config(args)
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())

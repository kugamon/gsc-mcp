#!/usr/bin/env python3
"""Structural validation for the gsc-seo plugin.

Run locally with `python3 scripts/validate_skills.py`; CI runs it on every push
and pull request. Exits non-zero on any error.

The checks exist because each one corresponds to a way this plugin has actually
broken, or could break silently:

  * absolute paths in .mcp.json      -> the original plugin was uninstallable
  * manifest version drift           -> a release tag that lies about its contents
  * frontmatter name != directory    -> the skill never triggers
  * vendored server drift            -> "unmodified copy" quietly stops being true
  * broken relative doc links        -> README promises a file that isn't there
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "gsc-seo"

# Directories the repo-wide walkers never descend into. `local/` holds untracked
# working material — archived bundles and a full clone of the upstream project —
# whose Markdown and relative links are not ours to validate.
SKIP_DIRS = {".git", ".venv", "venv", "local", "__pycache__", "node_modules"}


def skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)

errors: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Minimal YAML frontmatter reader.

    Handles `key: value` and `key: >` folded blocks, which is all these files
    use. Deliberately dependency-free so CI needs no pip install.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]

    fields: dict[str, str] = {}
    key: str | None = None
    buf: list[str] = []
    for raw in block.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", raw)
        if match:
            if key is not None:
                fields[key] = " ".join(buf).strip()
            key = match.group(1)
            value = match.group(2).strip()
            buf = [] if value in (">", "|", ">-", "|-") else [value]
        elif key is not None and raw.strip():
            buf.append(raw.strip())
    if key is not None:
        fields[key] = " ".join(buf).strip()
    return fields


# --------------------------------------------------------------- manifests --
def check_manifests() -> str | None:
    marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    plugin_path = PLUGIN / ".claude-plugin" / "plugin.json"

    for path in (marketplace_path, plugin_path):
        if not path.exists():
            error(f"missing manifest: {path.relative_to(ROOT)}")
            return None

    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error(f"manifest is not valid JSON: {exc}")
        return None

    entries = [p for p in marketplace.get("plugins", []) if p.get("name") == "gsc-seo"]
    if not entries:
        error("marketplace.json has no plugin entry named 'gsc-seo'")
        return None
    entry = entries[0]

    if entry.get("source") != "./plugins/gsc-seo":
        error(f"marketplace source should be ./plugins/gsc-seo, got {entry.get('source')!r}")

    version = plugin.get("version")
    if not version:
        error("plugin.json has no version")
    elif entry.get("version") != version:
        error(
            "version drift: marketplace.json says "
            f"{entry.get('version')!r}, plugin.json says {version!r}"
        )

    for field in ("name", "description", "author", "homepage", "license"):
        if not plugin.get(field):
            error(f"plugin.json is missing required field: {field}")

    return version


# ------------------------------------------------------------------ .mcp.json --
def check_mcp_config() -> None:
    """The regression test for this plugin's original sin."""
    path = PLUGIN / ".mcp.json"
    if not path.exists():
        error("missing plugins/gsc-seo/.mcp.json")
        return

    raw = path.read_text(encoding="utf-8")
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        error(f".mcp.json is not valid JSON: {exc}")
        return

    for bad in re.findall(r'"(/Users/[^"]*|/home/[^"]*|[A-Za-z]:\\\\[^"]*)"', raw):
        error(f".mcp.json contains a machine-specific absolute path: {bad}")

    servers = config.get("mcpServers", {})
    if "gsc-server" not in servers:
        error(".mcp.json does not declare a server named 'gsc-server'")
        return

    args = servers["gsc-server"].get("args", [])
    if not any("${CLAUDE_PLUGIN_ROOT}" in str(a) for a in args):
        error(".mcp.json args must reference ${CLAUDE_PLUGIN_ROOT}")

    env = servers["gsc-server"].get("env", {})
    if env.get("GSC_ALLOW_DESTRUCTIVE", "false").lower() not in ("false", "0", "no", ""):
        error("GSC_ALLOW_DESTRUCTIVE must ship as false — destructive tools stay opt-in")


# --------------------------------------------------------------------- skills --
EXPECTED_SKILLS = {
    "gsc-seo-analysis",
    "gsc-indexing-diagnostics",
    "gsc-site-profile",
    "gsc-report",
}

# Assets the skills reference by path. A skill promising a template that isn't
# there fails at the worst moment — mid-report, in front of whoever asked for it.
EXPECTED_ASSETS = {
    "report-template.html",
}


def check_skills(plugin_version: str | None) -> None:
    skills_dir = PLUGIN / "skills"
    if not skills_dir.is_dir():
        error("missing plugins/gsc-seo/skills/")
        return

    found = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    for missing in sorted(EXPECTED_SKILLS - found):
        error(f"expected skill directory not found: skills/{missing}")
    for extra in sorted(found - EXPECTED_SKILLS):
        warn(f"skill directory not in the expected set (update this script?): {extra}")

    for skill_dir in sorted(d for d in skills_dir.iterdir() if d.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            error(f"skills/{skill_dir.name}/ has no SKILL.md")
            continue

        fm = parse_frontmatter(skill_md)
        if not fm:
            error(f"skills/{skill_dir.name}/SKILL.md has no YAML frontmatter")
            continue

        if fm.get("name") != skill_dir.name:
            error(
                f"skills/{skill_dir.name}/SKILL.md: frontmatter name is "
                f"{fm.get('name')!r} but the directory is {skill_dir.name!r} — "
                "the skill will not trigger"
            )
        if fm.get("plugin") != "gsc-seo":
            error(f"skills/{skill_dir.name}/SKILL.md: frontmatter plugin should be 'gsc-seo'")
        if plugin_version and fm.get("version") != plugin_version:
            error(
                f"skills/{skill_dir.name}/SKILL.md: version {fm.get('version')!r} "
                f"does not match plugin.json {plugin_version!r}"
            )

        description = fm.get("description", "")
        if len(description) < 80:
            error(
                f"skills/{skill_dir.name}/SKILL.md: description is too short to "
                "trigger reliably — say when to use the skill, with the phrases "
                "a user would actually type"
            )


# ------------------------------------------------------------------ commands --
def check_commands() -> None:
    commands_dir = PLUGIN / "commands"
    if not commands_dir.is_dir():
        error("missing plugins/gsc-seo/commands/")
        return

    files = sorted(commands_dir.glob("*.md"))
    if not files:
        error("commands/ contains no .md files")

    for command in files:
        fm = parse_frontmatter(command)
        if not fm.get("description"):
            error(f"commands/{command.name}: missing a frontmatter description")


# -------------------------------------------------------------------- server --
def check_server() -> None:
    server_dir = PLUGIN / "server"
    required = [
        "gsc_server.py",
        "test_gsc_server.py",
        "run-server.sh",
        "requirements.txt",
        "UPSTREAM.md",
        "LICENSE.upstream",
    ]
    for name in required:
        if not (server_dir / name).exists():
            error(f"missing server/{name}")

    launcher = server_dir / "run-server.sh"
    if launcher.exists():
        body = launcher.read_text(encoding="utf-8")
        # Any bare echo to stdout corrupts the MCP stdio stream.
        for lineno, line in enumerate(body.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("echo ", "printf ")) and ">&2" not in line:
                error(
                    f"run-server.sh:{lineno} writes to stdout — this corrupts the "
                    "MCP protocol stream. Redirect to stderr."
                )

    # Both vendored files are hash-pinned. UPSTREAM.md records each on its own
    # labelled row, so match the filename and the digest together rather than
    # grabbing the first 16-hex string in the document.
    upstream_md = server_dir / "UPSTREAM.md"
    if upstream_md.exists():
        manifest = upstream_md.read_text(encoding="utf-8")
        for name in ("gsc_server.py", "test_gsc_server.py"):
            vendored = server_dir / name
            if not vendored.exists():
                continue
            digest = hashlib.sha256(vendored.read_bytes()).hexdigest()[:16]
            recorded = re.search(
                rf"`{re.escape(name)}`[^|]*\|\s*`([0-9a-f]{{16}})`", manifest
            )
            if not recorded:
                warn(f"UPSTREAM.md records no SHA-256 prefix for {name}")
            elif recorded.group(1) != digest:
                error(
                    f"{name} does not match the hash recorded in UPSTREAM.md "
                    f"(file is {digest}, UPSTREAM.md says {recorded.group(1)}). "
                    "Either the vendored copy was modified, or the re-sync did "
                    "not update UPSTREAM.md."
                )

    requirements = server_dir / "requirements.txt"
    if requirements.exists():
        for line in requirements.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" not in line:
                error(f"requirements.txt pin is not exact: {line!r}")


# ---------------------------------------------------------------- doc links --
def check_doc_links() -> None:
    """Every relative Markdown link must resolve to a real file."""
    for md in ROOT.rglob("*.md"):
        if skipped(md):
            continue
        text = md.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?://|mailto:|#)([^)#]+)", text):
            resolved = (md.parent / target.strip()).resolve()
            if not resolved.exists():
                error(f"{md.relative_to(ROOT)}: broken relative link -> {target.strip()}")


# ----------------------------------------------------------------- hygiene ---
def check_no_secrets() -> None:
    """Nothing that looks like a credential should ever be committed."""
    patterns = [
        (re.compile(r'"type"\s*:\s*"service_account"'), "a Google service-account key"),
        (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
        (re.compile(r'"client_secret"\s*:'), "an OAuth client secret"),
    ]
    self_path = Path(__file__).resolve()
    for path in ROOT.rglob("*"):
        if not path.is_file() or skipped(path) or path.resolve() == self_path:
            continue
        if path.suffix not in (".json", ".txt", ".md", ".pem", ".sh", ".py", ".yml", ".yaml"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern, label in patterns:
            if pattern.search(text):
                error(f"{path.relative_to(ROOT)} looks like it contains {label} — do not commit")


def check_assets() -> None:
    assets_dir = PLUGIN / "assets"
    for name in sorted(EXPECTED_ASSETS):
        path = assets_dir / name
        if not path.exists():
            error(f"missing assets/{name}")
            continue
        if path.suffix == ".html":
            text = path.read_text(encoding="utf-8")
            # The print stylesheet is the whole point of the template.
            for required in ("@page", "@media print", "page-break-inside"):
                if required not in text:
                    error(f"assets/{name} has no {required} rule — it will not print correctly")
            # Charts must stay dependency-free; a CDN script would break
            # offline, in email, and in any air-gapped review.
            if "<script src=" in text:
                error(
                    f"assets/{name} loads an external script. Charts are inline "
                    "SVG on purpose — see the gsc-report skill."
                )


def main() -> int:
    version = check_manifests()
    check_mcp_config()
    check_skills(version)
    check_commands()
    check_assets()
    check_server()
    check_doc_links()
    check_no_secrets()

    for message in warnings:
        print(f"warning: {message}")
    for message in errors:
        print(f"error: {message}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"OK — plugin gsc-seo v{version}, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

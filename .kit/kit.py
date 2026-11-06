#!/usr/bin/env python3
"""The repository kit (IF 362 to IF 364, IF 366): the same checks in every repository of ours, run on GitHub (and on
Forgejo) by .github/workflows/kit.yml on every push, every pull request and every night. Standard library only, so it
needs nothing installed. Published into each repository as .kit/kit.py by `experiverse.si.cli sites publish`.

  python3 .kit/kit.py check      drift, scope, secrets and append-only chains; exit 1 on any finding

Drift and scope: every file must be exactly as the record published it (MANIFEST.sha256, written at each publish);
a file changed, added or removed on GitHub by hand is drift. Secrets: no secret-shaped text (.kit/secret-patterns.txt,
from the record's own patterns). Append-only: a file named in .kit/chains.txt may only grow; no earlier line changes.
"""
import hashlib
import os
import re
import subprocess
import sys

SKIP = {".git"}
OWN = {"MANIFEST.sha256"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def files(root):
    """The files git would publish (tracked, or new and not ignored); a tree without git is walked instead."""
    if os.path.isdir(os.path.join(root, ".git")):
        r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True)
        if r.returncode == 0:
            names = sorted({n for n in r.stdout.decode("utf-8", "replace").split("\0") if n})
            return [n for n in names if n not in OWN and os.path.isfile(os.path.join(root, n))
                    and not os.path.islink(os.path.join(root, n))]
    out = []
    for d, ds, fs in os.walk(root):
        ds[:] = sorted(x for x in ds if x not in SKIP and not os.path.exists(os.path.join(d, x, ".git")))  # no submodules
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            if rel not in OWN and f != ".git":
                out.append(rel)
    return out


def manifest(root):
    """The lines of MANIFEST.sha256 for the tree as it is now (sha256sum format, sorted)."""
    return "".join(f"{sha256(os.path.join(root, p))}  {p}\n" for p in files(root))


def drift(root):
    p = os.path.join(root, "MANIFEST.sha256")
    if not os.path.exists(p):
        return ["MANIFEST.sha256 is missing: this repository was not published from the record"]
    want = {}
    for line in open(p, encoding="utf-8"):
        if line.strip():
            h, name = line.rstrip("\n").split("  ", 1)
            want[name] = h
    have = set(files(root))
    bad = [f"drift: {n} is missing" for n in sorted(set(want) - have)]
    bad += [f"drift: {n} was not published from the record (scope)" for n in sorted(have - set(want))]
    bad += [f"drift: {n} changed since it was published" for n in sorted(have & set(want))
            if sha256(os.path.join(root, n)) != want[n]]
    return bad


def secrets(root):
    p = os.path.join(root, ".kit", "secret-patterns.txt")
    pats = [re.compile(x.rstrip("\n")) for x in open(p, encoding="utf-8") if x.strip()] if os.path.exists(p) else []
    bad = []
    for n in files(root):
        if n.startswith(".kit/"):
            continue
        try:
            text = open(os.path.join(root, n), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if any(rx.search(text) for rx in pats):
            bad.append(f"secret-shaped text in {n}")
    return bad


def append_only(root):
    p = os.path.join(root, ".kit", "chains.txt")
    if not os.path.exists(p):
        return []
    bad = []
    for name in (x.strip() for x in open(p, encoding="utf-8")):
        if not name or not os.path.exists(os.path.join(root, name)):
            continue
        r = subprocess.run(["git", "show", f"HEAD~1:{name}"], cwd=root, capture_output=True)
        if r.returncode:                      # new in this commit, or no earlier commit: nothing to compare
            continue
        now = open(os.path.join(root, name), "rb").read()
        if not now.startswith(r.stdout):
            bad.append(f"append-only: {name} changed or lost earlier lines")
    return bad


def check(root):
    found = drift(root) + secrets(root) + append_only(root)
    for f in found:
        print(f"  {f}")
    print(f"kit: {'clean' if not found else str(len(found)) + ' finding(s)'} ({len(files(root))} files)")
    return 1 if found else 0


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(check(root) if sys.argv[1:2] == ["check"] else (print(__doc__) or 2))

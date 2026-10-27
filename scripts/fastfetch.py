#!/usr/bin/env python3
"""Fastfetch for AROS: pinned source, patch series, cross builds and packages.

  materialize          create work/fastfetch from the pin and the series
  status               commits and edits in work/ that are not in the series
  save                 export work/ commits after the series as new patches
  verify               rebuild the series in a temporary directory and compare
  build TARGET         configure and build from a fresh reconstruction
  package TARGET VER   assemble dist/<Name>-<VER>-<TARGET>.zip from a build
  test                 host tests of this repository's scripts

One commit in work/fastfetch is one patch. Nothing here resets, deletes or
replaces an existing work tree; operations that could lose work refuse.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "fastfetch"
TARGETS = ("aros-x86_64-abiv11-pc", "aros-x86_64-abiv1-pc", "aros-aarch64-abiv1-raspi")


def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


def out(args, **kw):
    return subprocess.check_output([str(a) for a in args], text=True, **kw)


def manifest():
    spec = json.loads((ROOT / "upstreams.json").read_text())["repositories"][REPO]
    if not re.fullmatch(r"[0-9a-f]{40}", spec.get("commit", "")):
        raise RuntimeError("upstreams.json: fastfetch needs a full 40-digit commit")
    return spec


def series():
    path = ROOT / "patches" / REPO / "series"
    if not path.exists():
        raise RuntimeError(f"{path} is missing; an empty file means no patches")
    names = [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]
    for n in names:
        if not (ROOT / "patches" / REPO / n).is_file():
            raise RuntimeError(f"series names {n}, which is not in patches/{REPO}/")
    return names


def check_upstream():
    p = ROOT / "upstream" / REPO
    head = out(["git", "-C", p, "rev-parse", "HEAD"]).strip()
    dirty = out(["git", "-C", p, "status", "--porcelain", "--untracked-files=all"])
    if head != manifest()["commit"] or dirty:
        raise RuntimeError(f"upstream/{REPO} must be clean at {manifest()['commit']}")
    return p


def reconstruct(dest):
    """The pin plus the whole series, as commits on branch aros, in dest."""
    upstream = check_upstream()
    if Path(dest).exists():
        raise RuntimeError(f"refusing to replace {dest}; preserve its files and Git history first")
    run(["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--no-hardlinks", upstream, dest])
    run(["git", "-C", dest, "checkout", "--quiet", "-B", "aros", manifest()["commit"]])
    env = dict(os.environ, GIT_COMMITTER_NAME="aros-fastfetch", GIT_COMMITTER_EMAIL="port@localhost",
               GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    for name in series():
        run(["git", "-C", dest, "am", "--quiet", "--keep-cr", "--committer-date-is-author-date",
             ROOT / "patches" / REPO / name], env=env)


def tree(repo, rev="HEAD"):
    """Paths with their mode and blob: contents and executable bits."""
    rows = out(["git", "-C", repo, "ls-tree", "-r", "--full-tree", rev]).splitlines()
    return {r.split("\t", 1)[1]: r.split("\t", 1)[0].split(" ")[0::2] for r in rows}


def work():
    w = ROOT / "work" / REPO
    if not (w / ".git").exists():
        raise RuntimeError(f"work/{REPO} does not exist: run materialize")
    return w


def inventory(w):
    """What a destructive operation would have to preserve."""
    return {
        "uncommitted": out(["git", "-C", w, "status", "--porcelain", "--untracked-files=all", "--ignored"]),
        "stashes": out(["git", "-C", w, "stash", "list"]),
        "branches": out(["git", "-C", w, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"]),
    }


def series_commits(w):
    """Commits on aros after the pin, oldest first."""
    pin = manifest()["commit"]
    if out(["git", "-C", w, "merge-base", pin, "HEAD"]).strip() != pin:
        raise RuntimeError("work/ HEAD does not descend from the pin")
    return out(["git", "-C", w, "rev-list", "--reverse", f"{pin}..HEAD"]).split()


def verify(quiet=False):
    """The saved series reproduces the saved part of work/, contents and modes."""
    w = work()
    commits = series_commits(w)
    saved = len(series())
    if len(commits) < saved:
        raise RuntimeError(f"work/ has {len(commits)} commits after the pin, the series {saved}")
    with tempfile.TemporaryDirectory(prefix="fastfetch-reproduce-") as d:
        dest = Path(d) / REPO
        reconstruct(dest)
        rev = commits[saved - 1] if saved else manifest()["commit"]
        if tree(dest) != tree(w, rev):
            raise RuntimeError(f"work/ at {rev[:12]} differs from the reconstructed series: "
                               "the saved commits were changed (amended?) after export")
    inv = inventory(w)
    if not quiet:
        print(f"series of {saved} patch(es) reproduces work/ at its commit {saved} (contents and modes)")
        if len(commits) > saved:
            print(f"{len(commits) - saved} commit(s) after the series, not saved yet")
        for k, v in inv.items():
            if v.strip() and not (k == "branches" and v.count("\n") == 1):
                print(f"{k}:\n{v.rstrip()}")
    return commits, saved


REQUIRED = ("Repository:", "Base:", "Problem:", "Solution:", "Scope:", "Upstream-Status:",
            "Verification:", "Removal:")


def save():
    w = work()
    commits, saved = verify(quiet=True)
    if inventory(w)["uncommitted"].strip():
        print("note: uncommitted changes in work/ are not saved; commit them first", file=sys.stderr)
    new = commits[saved:]
    if not new:
        print("nothing to save")
        return
    pdir = ROOT / "patches" / REPO
    names = series()
    number = 1 + max([int(n[:4]) for n in names if n[:4].isdigit()] + [0])
    for c in new:
        body = out(["git", "-C", w, "log", "-1", "--format=%B", c])
        missing = [k for k in REQUIRED if k not in body]
        if missing:
            raise RuntimeError(f"commit {c[:12]} lacks patch header fields: {', '.join(missing)}")
        subject = out(["git", "-C", w, "log", "-1", "--format=%s", c]).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:48]
        name = f"{number:04d}-{slug}.patch"
        if (pdir / name).exists():
            raise RuntimeError(f"{name} exists; not overwriting")
        data = out(["git", "-C", w, "format-patch", "-1", "--stdout", "--binary", "--no-signature",
                    "--zero-commit", c])
        if not data.strip():
            raise RuntimeError(f"commit {c[:12]} is empty")
        (pdir / name).write_text(data)
        names.append(name)
        (pdir / "series").write_text("".join(n + "\n" for n in names))
        print(f"saved {name}")
        number += 1
    verify()


def local_config():
    local = ROOT / "local.json"
    cfg = json.loads(local.read_text()) if local.exists() else {}
    return cfg


def build(target, source=None):
    if target not in TARGETS:
        raise RuntimeError(f"unknown target {target}; one of {', '.join(TARGETS)}")
    cfg = local_config().get(target, {})
    toolchain = ROOT / "cmake" / f"{target}.cmake"
    b = ROOT / "build" / target
    if b.exists():
        raise RuntimeError(f"{b} exists; remove it or keep it, but a build starts empty")
    b.mkdir(parents=True)
    src = b / "src"
    if source:
        shutil.copytree(source, src, ignore=shutil.ignore_patterns(".git"))
    else:
        reconstruct(src)
    defs = [f"-D{k}={v}" for k, v in sorted(cfg.items())]
    sdk = ROOT / "vendor" / "limpet-sdk"
    run(["cmake", "-S", src, "-B", b / "cmake", f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
         "-DCMAKE_BUILD_TYPE=Release", f"-DFF_AROS_LIMPET_SDK={sdk}", f"-DFF_AROS_TARGET={target}"] + defs)
    run(["cmake", "--build", b / "cmake", "--target", "fastfetch", "-j", str(os.cpu_count() or 4)])
    exe = b / "cmake" / "fastfetch"
    record = {"target": target, "upstream": manifest(), "series": series(),
              "patches_sha256": {n: hashlib.sha256((ROOT / "patches" / REPO / n).read_bytes()).hexdigest()
                                 for n in series()},
              "source": "work copy" if source else "reconstructed series",
              "fastfetch_sha256": hashlib.sha256(exe.read_bytes()).hexdigest()}
    (b / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"{target}: {exe} {record['fastfetch_sha256']}")


def package(target, version):
    b = ROOT / "build" / target
    record = json.loads((b / "build-record.json").read_text())
    if record["target"] != target:
        raise RuntimeError(f"{b} was built for {record['target']}")
    exe = b / "cmake" / "fastfetch"
    if hashlib.sha256(exe.read_bytes()).hexdigest() != record["fastfetch_sha256"]:
        raise RuntimeError(f"{exe} differs from its build record")
    run([sys.executable, ROOT / "scripts" / "package.py", target, version, b])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("action", choices=["materialize", "status", "save", "verify", "build", "package", "test"])
    p.add_argument("args", nargs="*")
    p.add_argument("--from-work", action="store_true", help="build: copy work/ instead of reconstructing")
    a = p.parse_args()
    if a.action == "materialize":
        reconstruct(ROOT / "work" / REPO)
    elif a.action == "status":
        verify()
    elif a.action == "save":
        save()
    elif a.action == "verify":
        verify()
    elif a.action == "build":
        build(a.args[0], ROOT / "work" / REPO if a.from_work else None)
    elif a.action == "package":
        package(a.args[0], a.args[1])
    else:
        run([sys.executable, "-m", "unittest", "discover", "-s", ROOT / "tests"])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError, KeyError) as e:
        print(f"fastfetch-port: {e}", file=sys.stderr)
        sys.exit(1)

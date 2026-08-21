"""Compute real Semantic Distinctness (S) and Cognitive Load (L) from a local git repo.

S = 1 - co-change fraction (from real commit history); L = structural complexity (LOC + files),
capacity held constant (N16 -> structural). Boundary = a matched top-level module directory.

Usage: python git_scl_scan.py <repo_path> [module_glob_prefix]
Read-only. Author: Viquar Khan. Copyright 2026 Viquar Khan.
"""
import subprocess, sys, os, collections

repo = sys.argv[1]
prefix = sys.argv[2] if len(sys.argv) > 2 else ""   # e.g. "spring-petclinic-"
CODE_EXT = ("java", "py", "js", "ts", "go", "rb", "kt", "scala", "cs", "xml")


def git(a):
    return subprocess.run(["git", "-C", repo, "-P"] + a, capture_output=True, text=True).stdout


def module_of(path):
    top = path.split("/")[0]
    if prefix and not top.startswith(prefix):
        return None
    return top


# ---- S: co-change over full history ----
log = git(["log", "--name-only", "--pretty=format:==%H"])
commits, cur = [], set()
for line in log.splitlines():
    if line.startswith("=="):
        if cur:
            commits.append(cur); cur = set()
    elif line.strip():
        m = module_of(line)
        if m:
            cur.add(m)
if cur:
    commits.append(cur)

touch = collections.Counter(); co = collections.Counter()
for c in commits:
    for m in c:
        touch[m] += 1
        if len(c) > 1:
            co[m] += 1


# ---- L: structural complexity from current tree ----
def bounded(x, k):
    return x / (x + k)

loc = collections.Counter(); files = collections.Counter()
for root, dirs, fs in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in (".git", "target", "build", "node_modules")]
    rel = os.path.relpath(root, repo).replace("\\", "/")
    m = module_of(rel)
    if not m:
        continue
    for f in fs:
        if f.rsplit(".", 1)[-1].lower() in CODE_EXT:
            try:
                loc[m] += sum(1 for _ in open(os.path.join(root, f), encoding="utf-8", errors="ignore"))
                files[m] += 1
            except Exception:
                pass

mods = sorted([m for m in touch if loc[m] > 0], key=lambda k: -touch[k])
print(f"repo: {os.path.basename(repo.rstrip('/'))}   commits: {len(commits)}   modules: {len(mods)}\n")
print(f"{'service (boundary)':40}{'changesets':>11}{'S':>7}{'LOC':>7}{'files':>7}{'L':>7}")
rows = []
for m in mods:
    S = 1.0 - (co[m] / touch[m]) if touch[m] else 1.0
    L = min(1.0, (bounded(loc[m], 3000) + bounded(files[m], 30)) / 2.0)
    rows.append((m, S, L))
    short = m.replace(prefix, "") if prefix else m
    print(f"{short[:38]:40}{touch[m]:>11}{S:>7.3f}{loc[m]:>7}{files[m]:>7}{L:>7.3f}")

if rows:
    Ss = [r[1] for r in rows]; Ls = [r[2] for r in rows]
    print(f"\nREAL S: min {min(Ss):.3f} mean {sum(Ss)/len(Ss):.3f} max {max(Ss):.3f}")
    print(f"REAL L: min {min(Ls):.3f} mean {sum(Ls)/len(Ls):.3f} max {max(Ls):.3f}")
    # write a feature-table stub for later join with E + outcomes
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       os.path.basename(repo.rstrip("/\\")).lstrip("_") + "_SL.csv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("service,S,L\n")
        for m, S, L in rows:
            f.write(f"{m},{round(S,3)},{round(L,3)}\n")
    print(f"wrote {out}  (join with measured E and outcomes to complete the study)")

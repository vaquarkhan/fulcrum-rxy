"""Run the Fulcrum real-deployment testbed and measure real Kinetic Efficiency.

Launches several real service processes that talk to each other over real HTTP, drives load,
reads each service's self-measured E, then scores them and tests whether measured E separates
the engineered healthy boundaries from the engineered distributed-monolith boundaries.

HONEST FRAMING: the good/bad LABELS come from the known engineered design (chatty vs clean),
but E is REALLY MEASURED from a real running distributed system over real HTTP. This validates
that the E measurement pipeline works on a real deployment and produces the correct signature
(low E for chatty distributed monoliths, high E for healthy boundaries). It is a measurement /
face-validity result, not a predictive-power claim (that is Experiment 3 and the production study).

Runs locally with stdlib only (no Docker, no cloud needed). The identical services also run on
EC2 via docker-compose if a cloud deployment is wanted; the measurement is the same.
Author: Viquar Khan. Copyright 2026 Viquar Khan.
"""
import os, sys, time, json, subprocess, urllib.request, threading, signal

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# topology: (name, port, useful_ms, hops, downstream_port, label)  label 1=healthy 0=distributed-monolith
# Healthy services call their OWN dedicated leaf to avoid a shared-bottleneck confound.
SERVICES = [
    ("leaf-h1",     8101,  4, 0, None, None),   # dedicated leaf for aggregator
    ("leaf-h2",     8102,  4, 0, None, None),   # dedicated leaf for reporter
    ("leaf-c",      8103,  4, 0, None, None),   # leaf for chatty services
    ("standalone",  8104, 40, 0, None, 1),      # healthy: all local work
    ("aggregator",  8105, 25, 1, 8101, 1),      # healthy: one downstream call
    ("reporter",    8106, 30, 1, 8102, 1),      # healthy: one downstream call
    ("chatty-a",    8107,  4, 8, 8103, 0),      # distributed monolith: 8 synchronous hops
    ("chatty-b",    8108,  3, 10, 8103, 0),     # distributed monolith: 10 synchronous hops
    ("coupled",     8109,  5, 6, 8107, 0),      # distributed monolith: 6 hops into chatty-a
]

procs = []


def start_all():
    for name, port, useful, hops, dport, _ in SERVICES:
        env = dict(os.environ, SERVICE_NAME=name, PORT=str(port), USEFUL_MS=str(useful),
                   HOPS=str(hops), DOWNSTREAM=(f"http://127.0.0.1:{dport}" if dport else ""))
        p = subprocess.Popen([PY, os.path.join(HERE, "service.py")], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p)
    time.sleep(3.5)


def stats_retry(port, tries=4):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/stats", timeout=10).read())
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("stats unavailable")


def hit(port, n):
    for _ in range(n):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/work", timeout=15).read()
        except Exception:
            pass


def load(requests_per_service=24, concurrency=3):
    targets = [(port) for (name, port, *_1, label) in SERVICES if label is not None]
    threads = []
    for port in targets:
        per = requests_per_service // concurrency
        for _ in range(concurrency):
            t = threading.Thread(target=hit, args=(port, per)); t.start(); threads.append(t)
    for t in threads:
        t.join()


def stats(port):
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/stats", timeout=10).read())


def rank_auc(pairs):
    pos = [s for s, y in pairs if y == 1]; neg = [s for s, y in pairs if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum((sp > sn) + 0.5 * (sp == sn) for sp in pos for sn in neg)
    return wins / (len(pos) * len(neg))


def main():
    print("Launching real service processes (real HTTP between them)...")
    start_all()
    print("Driving load...")
    load()
    time.sleep(0.5)
    print("\nMeasured Kinetic Efficiency from the real running system:")
    print(f"{'service':14}{'label':>18}{'requests':>10}{'E (measured)':>14}")
    rows = []
    for name, port, useful, hops, dport, label in SERVICES:
        try:
            s = stats_retry(port)
        except Exception as e:
            print(f"{name:14} stats error {e}"); continue
        E = s.get("E")
        lab = "-" if label is None else ("healthy" if label == 1 else "distributed-monolith")
        Es = f"{E:.3f}" if E is not None else "n/a"
        print(f"{name:14}{lab:>18}{s.get('count',0):>10}{Es:>14}")
        if label is not None and E is not None:
            rows.append((name, E, label))
    if rows:
        auc = rank_auc([(E, y) for _, E, y in rows])
        print(f"\nSeparation by MEASURED E (healthy vs distributed-monolith): AUC = {auc:.3f}")
        print("AUC near 1.0 means measured E cleanly identifies the distributed-monolith boundaries.")
    print("\nHONEST SCOPE: E is really measured from a real running distributed system over real HTTP.")
    print("Labels are the engineered design. This validates E measurement + face validity on a real")
    print("deployment; it is not a predictive-power claim (that is Experiment 3 / the production study).")
    # write feature table
    with open(os.path.join(HERE, "testbed_E.csv"), "w", encoding="utf-8") as f:
        f.write("service,E,label\n")
        for n, E, y in rows:
            f.write(f"{n},{round(E,3)},{y}\n")


def cleanup(*a):
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()

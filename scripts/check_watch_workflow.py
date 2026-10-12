"""Check the approved manual-watch HTTP workflow in a disposable directory.

The server may start bounded read-only market requests after an add; no
assertion depends on a provider response. No real membership, labels or paper
state is mutated. Run with ``uv run python scripts/check_watch_workflow.py``.
"""

import argparse
from hashlib import sha256
import http.client
import json
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4177)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    # Capture preservation for this run, so later legitimate human training
    # work does not make a historical delivery baseline a permanent lock.
    previous = {path: sha256(path.read_bytes()).hexdigest() for path in (root / "private").rglob("*")
                if path.is_file() and root / "private" / "watch" not in path.parents}
    previous.update({path: sha256(path.read_bytes()).hexdigest() for path in
                     (root / "src/gary/patterns.py", root / "src/gary/review.py", root / "src/gary/evaluation.py",
                      root / "src/gary/static/stock-lists.json")})
    server = None

    def request(method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", args.port, timeout=5)
        payload = None if body is None else json.dumps(body)
        connection.request(method, path, payload, {"Content-Type": "application/json", **(headers or {})})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def start(directory):
        process = subprocess.Popen([sys.executable, "-m", "gary.preview", "--port", str(args.port), "--watch-dir", str(directory)],
                                   cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            # Observe our child binding its own socket before requesting it.
            # Never mistake an existing preview on this port for disposable QA.
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=5):
                    raise RuntimeError("Disposable server startup timed out")
                started = process.stdout.readline().strip()
                if started != f"Gary.ai synthetic paper preview: http://127.0.0.1:{args.port}":
                    raise RuntimeError("Disposable server did not start; choose a free --port")
            for _ in range(50):
                if process.poll() is not None:
                    raise RuntimeError("Disposable server did not start; choose a free --port")
                try:
                    status, result = request("GET", "/api/watch")
                    if status == 200:
                        return process, result
                except OSError:
                    pass
                time.sleep(0.05)
            raise RuntimeError("Disposable server startup timed out")
        except BaseException:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
            raise

    try:
        with tempfile.TemporaryDirectory(prefix="gary-watch-workflow-") as directory:
            server, view = start(directory)
            assert view["manual_list"] == view["radar_list"] == view["buy_ready_list"] == []
            assert request("POST", "/api/watch/add", {"symbol": "../DEMO"})[0] == 400
            assert request("POST", "/api/watch/add", {"symbol": "DEMO", "directory": "/tmp/escape"})[0] == 400
            assert request("POST", "/api/watch/add?root=/tmp/escape", {"symbol": "DEMO"})[0] == 400
            assert request("POST", "/api/watch/add", {"symbol": "DEMO"}, {"Origin": "https://outside.example"})[0] == 403
            assert request("GET", "/api/watch", headers={"Host": "outside.example"})[0] == 403
            assert request("POST", "/api/watch/add", {"symbol": "DEMO"}, {"Content-Type": "text/plain"})[0] == 400
            assert request("POST", "/api/watch/add", {"symbol": "DEMO", "note": "x" * 17000})[0] == 400
            status, view = request("POST", "/api/watch/add", {"symbol": "BRK.B", "note": "Synthetic QA; no eligibility implied."})
            assert status == 200 and view["manual_list"][0]["symbol"] == "BRK-B"
            assert view["radar_list"] == view["buy_ready_list"] == []
            entry = view["manual_list"][0]
            assert entry["why"] and len(entry["checks"]) == 7
            added_at = entry["added_at"]
            status, view = request("POST", "/api/watch/add", {"symbol": "brk-b"})
            assert status == 200 and len(view["manual_list"]) == 1
            assert view["manual_list"][0]["note"].startswith("Synthetic") and view["manual_list"][0]["added_at"] == added_at
            server.terminate()
            server.wait(timeout=5)
            server, view = start(directory)
            assert view["manual_list"][0]["added_at"] == added_at
            status, data = request("GET", "/api/stock-lists")
            assert status == 200 and len(data["sell_list"]) == 10 and len(data["watch"]["manual_list"]) == 1
            status, view = request("POST", "/api/watch/remove", {"symbol": "BRK.B"})
            assert status == 200 and view["manual_list"] == []
            assert request("POST", "/api/watch/remove", {"symbol": "BRK.B"})[0] == 200
            assert request("POST", "/api/watch/refresh", {"symbol": "BRK-B"})[0] == 400
            membership = Path(directory) / "membership.json"
            state = json.loads(membership.read_text())
            assert len(state["archive"]) == 1 and state["archive"][0]["note"].startswith("Synthetic")
            membership.write_text("corrupt")
            assert request("GET", "/api/watch")[0] == 400 and membership.read_text() == "corrupt"
            server.terminate()
            server.wait(timeout=5)
            server = None
        assert all(path.exists() and sha256(path.read_bytes()).hexdigest() == digest for path, digest in previous.items())
        print(f"Watch HTTP workflow passed; {len(previous)} pre-existing evidence/source files preserved.")
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()

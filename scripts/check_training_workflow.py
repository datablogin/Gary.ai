"""Independent Train more QA through approved HTTP/domain boundaries.

All invented sources and observations live below one disposable temp root.
Real retained artifacts are inspected only by byte hashes or public structural
projections. Child servers are owned by this process and always closed.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from http.client import RemoteDisconnected
import json
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gary import training
from gary.training_preview import prepare_store


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = runpy.run_path(str(ROOT / "tests/test_training.py"))
CARD_FIELDS = {"case_id", "bars", "target_start_offset", "target_end_offset", "price_basis", "volume_available"}
BAR_FIELDS = {"offset", "open", "high", "low", "close", "volume"}
LABEL_FIELDS = {"case_id", "reviewer_id", "reviewer_role", "decision", "rationale", "revision", "events"}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return sha256(encoded(value)).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(encoded(value))


def tree_hashes(directory):
    return {str(p.relative_to(directory)): file_hash(p) for p in sorted(directory.rglob("*")) if p.is_file()}


def preservation_guard():
    baseline = json.loads((ROOT / "private/training/preservation-baseline.json").read_text())
    require(baseline["schema_version"] == "training-preservation-v1" and len(baseline["files"]) == 430,
            "Expected the frozen 430-file preservation baseline")
    require(all(file_hash(ROOT / p) == expected for p, expected in baseline["files"].items()),
            "An original artifact received-byte fingerprint changed")
    return digest(baseline)


def synthetic_store(directory, count=2, change=None):
    """Retain independent raw, metadata and proof bytes before operator import."""
    catalog, _, request = FIXTURES["round_fixture"](count)
    if change:
        change(catalog)
    inputs = directory / "inputs"
    inputs.mkdir(parents=True)
    proof = inputs / "lineage-classification-exposure.json"
    write_json(proof, {"schema_version": "synthetic-qa-evidence-v1", "synthetic": True})
    receipts = [{"path": str(proof), "received_sha256": file_hash(proof)}]
    catalog["exposure"]["evidence"] = deepcopy(receipts)
    source_receipts = []
    for source in catalog["sources"]:
        source["alias_evidence"]["receipt_sha256"] = file_hash(proof)
        source["classification"]["evidence_sha256"] = file_hash(proof)
        raw = inputs / (source["source_id"] + ".raw.json")
        metadata = inputs / (source["source_id"] + ".metadata.json")
        write_json(raw, {k: source[k] for k in ("symbol", "exchange_timezone", "bars", "split_dates")})
        source["source_sha256"] = file_hash(raw)
        write_json(metadata, {k: v for k, v in source.items() if k not in {"bars", "source_sha256"}})
        receipts.extend({"path": str(p), "received_sha256": file_hash(p)} for p in (raw, metadata))
        source_receipts.append({"source_id": source["source_id"], "format": "synthetic-ohlcv-v1",
                                "raw_path": str(raw), "metadata_path": str(metadata)})
    prepare_store(directory, catalog, request["config"], source_receipts, receipts)
    return catalog


class Client:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"

    def request(self, path, body=None, expected=200, headers=None):
        request_headers = {"Origin": self.base}
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})
        request = Request(self.base + path, data=encoded(body) if body is not None else None, headers=request_headers)
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            require(response.status == expected, f"{path}: expected HTTP {expected}, received {response.status}: {payload[:250]!r}")
            require(response.headers.get("Cache-Control") == "no-store", "Training responses must disable caching")
            return json.loads(payload) if response.headers.get_content_type() == "application/json" else payload.decode()

    def hub(self, round_id=None):
        return self.request("/api/training" + ("?" + urlencode({"round_id": round_id}) if round_id else ""))

    def card(self, selected, case_id):
        return self.request("/api/training/card?" + urlencode({"round_id": selected["round_id"], "case_id": case_id}))

    def round(self, request_id):
        return self.request("/api/training/round", {"request_id": request_id})

    def label(self, selected, case_id, **changes):
        card = self.card(selected, case_id)
        entry = dict(round_id=selected["round_id"], case_id=case_id, reviewer_id="gary", decision="none",
                     rationale="Disposable synthetic engineering control.", events=[], expected_revision=0,
                     revise=False, view_token=card["view_token"])
        return self.request("/api/training/label", entry | changes)


@contextmanager
def server(directory, port, package=None, fault=None):
    with socket.socket() as check:
        require(check.connect_ex(("127.0.0.1", port)) != 0, f"Port {port} is already in use; no existing server was touched")
    log = directory.parent / (directory.name + ".server.log")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(package or ROOT / "src")
    command = [sys.executable, "-m", "gary.preview", "--cycle-3", "--port", str(port), "--training-dir", str(directory)]
    if fault:
        command = [sys.executable, str(Path(__file__).resolve()), "--child-training-dir", str(directory),
                   "--port", str(port), "--fault", fault]
    with log.open("wb") as output:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=output, stderr=output)
        client = Client(port)
        try:
            deadline = time.monotonic() + 15
            while True:
                require(process.poll() is None, "Owned preview exited before readiness: " + log.read_text()[-500:])
                try:
                    client.request("/health")
                    break
                except (URLError, ConnectionError):
                    require(time.monotonic() < deadline, "Owned preview readiness deadline exceeded")
                    time.sleep(0.05)
            yield client, process
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def exhausted_data_probe(root, port):
    directory = root / "exhaustion"
    synthetic_store(directory, count=1)
    with server(directory, port) as (client, _):
        created = client.round("one-target")
        selected = created["round"]
        require(len(selected["order"]) == 1, "Literal single-source flat fixture must yield one target")
        completed = client.label(selected, selected["order"][0])
        require(completed["status"] == "complete", "Acknowledged last save must seal the round")
        outcome = client.round("exhausted-targets")
        require(outcome["outcome"] == "needs_data", "Previously labeled target must not be allocated again")
        reloaded = client.hub()
        require(reloaded["status"] == "needs_data" and reloaded["message"],
                "Durable latest needs_data outcome is hidden on hub reload after completed round")
        require(client.hub(selected["round_id"])["round"]["diagnostic"]["status"] == "complete",
                "Completed history must remain independently readable")
    with server(directory, port) as (client, _):
        require(client.hub()["status"] == "needs_data", "Data-needed state must survive restart")


def anonymous_card(view):
    require(set(view) == {"card", "overview", "own_label", "view_token"}, "Card projection leaks private fields")
    require(set(view["card"]) == CARD_FIELDS and set(view["overview"]) == CARD_FIELDS | {"split_offsets"},
            "Card fields must be anonymous allowlisted fields")
    require(len(view["card"]["bars"]) == 180 and len(view["overview"]["bars"]) == 1305,
            "Literal five-year fixture must keep 1305 overview sessions separate from exact180 detail")
    for card in (view["card"], view["overview"]):
        require(card["bars"][0]["close"] == 100 and card["target_start_offset"] == -19 and card["target_end_offset"] == 0,
                "Card normalization or final20 target changed")
        require([b["offset"] for b in card["bars"]] == list(range(1 - len(card["bars"]), 1))
                and all(set(b) == BAR_FIELDS for b in card["bars"]), "Anonymous OHLCV must use continuous relative offsets")
    if view["own_label"]:
        require(set(view["own_label"]) == LABEL_FIELDS, "Own label projection leaks generated receipts")


def immutable_snapshots(directory):
    return {str(p.relative_to(directory)): file_hash(p) for folder in ("passes", "reports")
            for p in (directory / folder).glob("*.json")}


def workflow_probe(root, port):
    directory = root / "workflow"
    synthetic_store(directory, count=2)
    with server(directory, port) as (client, _):
        require('/learn' in client.request("/") and '/learn' in client.request("/review"), "Both application entry points need Train more")
        require('/api/training' in client.request("/learn"), "Learn page must use the integrated training API")
        require(client.hub()["round"] is None, "Prepared state must not automatically allocate a round")
        created = client.round("qa-create")
        selected = created["round"]
        require(created["outcome"] == "created" and created["status"] == "ready" and len(selected["order"]) == 2,
                "First explicit request must allocate the literal two-source smaller batch")
        require(selected["diagnostic"] is None and selected["own_labels"] == {}, "Incomplete batch must hide committed answers")
        for case_id in selected["order"]:
            anonymous_card(client.card(selected, case_id))
        retry = client.round("qa-create")
        require(retry["round"] == selected and len(retry["history"]) == 1, "Double click must retain one immutable allocation")
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(client.round, [f"parallel-{n}" for n in range(6)]))
        require(all(r["round"]["round_id"] == selected["round_id"] and len(r["history"]) == 1 for r in results),
                "Parallel round requests allocated competing active rounds")
        before = tree_hashes(directory)
        client.request("/api/training?reviewer=agent", expected=403)
        client.request("/api/training?training_dir=/tmp/arbitrary", expected=400)
        client.request("/api/training", expected=403, headers={"Host": "untrusted.example"})
        client.request("/api/training/round", {"request_id": "cross-origin"}, expected=403, headers={"Origin": "https://untrusted.example"})
        client.request("/api/training/round", {"request_id": "override", "version": "arbitrary-module"}, expected=400)
        client.request("/api/training/round", {"request_id": "x" * 17000}, expected=400)
        first = selected["order"][0]
        valid = dict(round_id=selected["round_id"], case_id=first, reviewer_id="gary", decision="none", rationale="synthetic",
                     events=[], expected_revision=0, revise=False, view_token=client.card(selected, first)["view_token"])
        client.request("/api/training/label", valid | {"reviewer_id": "agent"}, expected=403)
        client.request("/api/training/label", valid | {"view_token": "0" * 64}, expected=400)
        require(tree_hashes(directory) == before, "Rejected identity/origin/token/envelope requests changed store bytes")
        with ThreadPoolExecutor(max_workers=2) as executor:
            simultaneous = list(executor.map(lambda _: client.label(selected, first), range(2)))
        partial = simultaneous[-1]
        require(simultaneous[0]["round"] == partial["round"], "Concurrent identical saves produced divergent label history")
        require(partial["status"] == "labeling" and partial["round"]["progress"]["labeled"] == 1
                and partial["round"]["diagnostic"] is None, "Acknowledged incomplete save must expose only own progress")
        anonymous_card(client.card(selected, first))
        acknowledged = tree_hashes(directory)
        client.label(selected, first)
        require(tree_hashes(directory) == acknowledged, "Identical acknowledged label retry appended or rewrote evidence")
        for case_id in selected["order"][1:]:
            completed = client.label(selected, case_id)
        diagnostic = completed["round"]["diagnostic"]
        require(completed["status"] == "complete" and diagnostic["mode"] == "single_investor_diagnostic"
                and diagnostic["reference_detector_input_sessions"] == 180 and diagnostic["visual_context_years"] == 5,
                "Completed report must be explicitly a personal180-reference/five-year diagnostic")
        require("inventory" not in diagnostic and "reference_hash" not in diagnostic, "Completed projection leaks case mappings/receipts")
        original = immutable_snapshots(directory)
        require(len(original) == 2, "Initial complete round must retain one pass and one report")
        revised = client.label(selected, first, decision="uncertain", expected_revision=1, revise=True)
        require(revised["round"]["snapshot_count"] == 2 and revised["round"]["diagnostic"]["pass_hash"] != diagnostic["pass_hash"],
                "Explicit completed revision must produce a separate development snapshot")
        require(all(file_hash(directory / p) == h for p, h in original.items()), "Completed revision replaced the earlier pass/report")
        revised_state = revised["round"]
    # Process death after the response is acknowledged must retain every label and revision.
    with server(directory, port) as (client, process):
        require(client.hub(selected["round_id"])["round"] == revised_state, "Restart lost acknowledged complete/revised state")
        process.kill()
        process.wait(timeout=5)
    # Materialized caches are disposable; remove only synthetic files beneath our temp root.
    (directory / "history.json").unlink()
    for folder in ("queues", "passes", "reports"):
        shutil.rmtree(directory / folder)
    with (directory / "events.journal.jsonl").open("ab") as journal:
        journal.write(b'{"unacknowledged_partial_tail":')
    unchanged = tree_hashes(directory)
    with server(directory, port) as (client, _):
        require(client.hub(selected["round_id"])["round"] == revised_state, "Cache loss/partial tail lost acknowledged labels")
        invalid = valid | {"view_token": "0" * 64, "expected_revision": 2, "revise": True}
        client.request("/api/training/label", invalid, expected=400)
        missing = deepcopy(invalid)
        del missing["view_token"]
        client.request("/api/training/label", missing, expected=400)
        require(tree_hashes(directory) == unchanged, "Rejected token repaired a tail or wrote materialized state")
        retry = client.label(selected, first, decision="uncertain", expected_revision=1, revise=True)
        require(retry["round"] == revised_state, "Valid recovery retry changed acknowledged revision")
        require(list((directory / "interrupted").glob("*.raw")) and len(immutable_snapshots(directory)) == 4,
                "Valid recovery must archive partial tail and rebuild immutable evidence")
        require(all(file_hash(directory / p) == h for p, h in original.items()), "Cache reconstruction changed prior report/pass bytes")
        require(len(client.hub()["history"]) == 1, "Recovery fabricated a second round")


def admission_probe(root, port):
    def missing_complete(catalog):
        catalog["exposure"]["complete"] = False

    def missing_alias(catalog):
        del catalog["exposure"]["aliases"][catalog["sources"][0]["symbol"]]

    def alias_chain(catalog):
        source = catalog["sources"][0]
        catalog["exposure"]["aliases"][source["canonical_id"]] = "different-canonical"

    def target(catalog):
        source = catalog["sources"][0]
        catalog["exposure"]["targets"].append(dict(canonical_id=source["symbol"], start="2025-04-11", end="2025-04-11",
                                                 case_fingerprint="e" * 64, provenance="synthetic prior labeled target"))

    def reserved_source(catalog):
        source = catalog["sources"][0]
        catalog["exposure"]["reservations"].append(dict(canonical_id=source["symbol"], start="2030-01-01", end="2030-01-02",
                                                      active=True, provenance="synthetic future-validation issuer"))

    def reserved_context(catalog):
        catalog["exposure"]["aliases"]["other-source"] = "other-issuer"
        catalog["exposure"]["reservations"].append(dict(canonical_id="other-issuer", start="2021-01-01", end="2021-01-02",
                                                      active=True, provenance="synthetic reserved full-view interval"))

    def missing_view_interval(catalog):
        source = catalog["sources"][0]
        catalog["exposure"]["views"].append(dict(canonical_id=source["symbol"], end="2021-01-02", provenance="incomplete prior view"))

    controls = {"missing-exposure": missing_complete, "missing-alias": missing_alias, "alias-chain": alias_chain,
                "target-reuse": target, "reserved-issuer": reserved_source, "reserved-full-context": reserved_context,
                "missing-full-view": missing_view_interval}
    for name, change in controls.items():
        directory = root / name
        synthetic_store(directory, count=1, change=change)
        with server(directory, port) as (client, _):
            result = client.round(name)
            require(result["outcome"] == "needs_data" and result["round"] is None and not result["history"],
                    name + ": provenance/alias/target/reservation violation allocated a round")
            require(client.hub()["status"] == "needs_data", name + ": non-round outcome was not durable")
    # Missing top-level provenance at the approved pure seam also cannot mean empty exposure.
    for field in ("evidence", "targets", "views", "reservations"):
        catalog, history, request = FIXTURES["round_fixture"](1)
        del catalog["exposure"][field]
        history["exposure"] = deepcopy(catalog["exposure"])
        require(training.request_training_round(catalog, history, request)["status"] == "needs_data",
                "Missing " + field + " silently initialized empty provenance")
    source = FIXTURES["synthetic_source"]()
    settings = FIXTURES["config"]([source])
    prior = dict(canonical_id=source["symbol"], start="2021-01-01", end="2022-01-01", provenance="synthetic prior display")
    settings["exposure"]["views"] = [prior]
    queue = training.build_review_queue([source], settings)
    require(len(queue["order"]) == 1 and queue["sealed"]["cases"][queue["order"][0]]["prior_view_overlap"] == [prior]
            and queue["sealed"]["cases"][queue["order"][0]]["development_only"] is True,
            "Broader prior view must remain explicitly development exposure")
    catalog, history, request = FIXTURES["round_fixture"](1)
    created = training.request_training_round(catalog, history, request)
    altered = deepcopy(request)
    altered["config"]["random_seed"] += 1
    untouched = deepcopy(created["history"])
    try:
        training.request_training_round(catalog | {"exposure": created["history"]["exposure"]}, created["history"], altered)
    except ValueError:
        pass
    else:
        raise AssertionError("Changed payload reused a durable request id")
    require(created["history"] == untouched, "Conflicting request mutated authoritative history")


def subsequent_round_probe(root, port):
    directory = root / "subsequent-round"
    synthetic_store(directory, count=7)
    with server(directory, port) as (client, _):
        first = client.round("first-six")["round"]
        require(len(first["order"]) == 6, "Seven flat sources must produce the bounded six-random first batch")
        for case_id in first["order"]:
            complete = client.label(first, case_id)
        require(complete["status"] == "complete", "First batch did not complete")
        previous = immutable_snapshots(directory)
        next_hub = client.round("remaining-one")
        second = next_hub["round"]
        require(next_hub["outcome"] == "created" and second["round_id"] != first["round_id"] and len(second["order"]) == 1
                and len(next_hub["history"]) == 2, "Completed batch did not permit a distinct honest smaller subsequent round")
        require(set(second["order"]).isdisjoint(first["order"]), "Subsequent round reused an old case")
        old_retry = client.round("first-six")
        require(old_retry["round"]["round_id"] == first["round_id"] and len(old_retry["history"]) == 2,
                "Retrying an earlier completed request changed round allocation")
        require(client.hub()["round"]["round_id"] == second["round_id"], "Hub must resume the sole new active round")
        require(client.hub(first["round_id"])["round"]["diagnostic"] == complete["round"]["diagnostic"],
                "Subsequent round changed the earlier completed report")
        require(all(file_hash(directory / p) == h for p, h in previous.items()), "Subsequent round changed earlier immutable evidence")
    with server(directory, port) as (client, _):
        require(client.hub()["round"] == second, "Restart did not resume the subsequent active round")


def rebind_bootstrap_header(directory, bootstrap):
    """Adversarial coherent self-hashes deliberately retain independent raw anchors."""
    write_json(directory / "bootstrap.json", bootstrap)
    header = dict(schema_version="training-journal-v1", bootstrap_hash=digest(bootstrap))
    (directory / "events.journal.jsonl").write_bytes(encoded(header) + b"\n")


def tamper_probe(root, port):
    for name in ("catalog-bars", "manifest", "profile", "raw-receipt", "missing-receipt"):
        directory = root / ("tamper-" + name)
        synthetic_store(directory, count=1)
        bootstrap = json.loads((directory / "bootstrap.json").read_text())
        if name == "catalog-bars":
            bootstrap["catalog"]["sources"][0]["bars"][-1]["volume"] += 1
            # Even a plausible self-declared source hash cannot replace retained raw bytes.
            bootstrap["catalog"]["sources"][0]["source_sha256"] = digest(bootstrap["catalog"]["sources"][0]["bars"])
            rebind_bootstrap_header(directory, bootstrap)
        elif name == "manifest":
            bootstrap["config"]["detector_manifest"]["parameter_hash"] = "0" * 64
            rebind_bootstrap_header(directory, bootstrap)
        elif name == "profile":
            bootstrap["config"]["profile"] = "five-year-pretend-v2"
            rebind_bootstrap_header(directory, bootstrap)
        elif name == "raw-receipt":
            raw = Path(bootstrap["source_receipts"][0]["raw_path"])
            data = json.loads(raw.read_text())
            data["bars"][-1]["volume"] += 1
            write_json(raw, data)
        else:
            Path(bootstrap["source_receipts"][0]["raw_path"]).unlink()
        before = tree_hashes(directory)
        with server(directory, port) as (client, _):
            if name != "profile":
                client.request("/api/training", expected=400)
            client.request("/api/training/round", {"request_id": "tampered"}, expected=400)
        require(tree_hashes(directory) == before, name + ": failed anchor validation mutated state")
    # Content fingerprints must invalidate a warm cache even when file size and
    # filesystem timestamps are unchanged.
    directory = root / "tamper-warm-cache"
    synthetic_store(directory, count=1)
    with server(directory, port) as (client, _):
        selected = client.round("warm-cache")["round"]
        client.hub()
        bootstrap = json.loads((directory / "bootstrap.json").read_text())
        raw = Path(bootstrap["source_receipts"][0]["raw_path"])
        original_stat = raw.stat()
        original = raw.read_bytes()
        changed = original.replace(b'"volume":1000', b'"volume":1001', 1)
        require(changed != original and len(changed) == len(original), "Literal same-size raw tamper fixture failed")
        raw.write_bytes(changed)
        os.utime(raw, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        before = tree_hashes(directory)
        client.request("/api/training/card?" + urlencode({"round_id": selected["round_id"], "case_id": selected["order"][0]}), expected=400)
        require(tree_hashes(directory) == before, "Warm-cache tamper rejection rewrote state")
    # An altered queue sidecar with coherent reference and queue self-hashes must
    # still fail against the independently retained journal/source reconstruction.
    directory = root / "tamper-sidecar-protocol"
    synthetic_store(directory, count=1)
    with server(directory, port) as (client, _):
        selected = client.round("sidecar-original")["round"]
        path = next((directory / "queues").glob("*.json"))
        queue = json.loads(path.read_text())
        reference = queue["sealed"]["reference"]
        reference["protocol"]["match_tolerance_sessions"] = 4
        reference["commitment_hash"] = digest({k: v for k, v in reference.items() if k != "commitment_hash"})
        queue["queue_hash"] = digest({k: v for k, v in queue.items() if k != "queue_hash"})
        write_json(path, queue)
        before = tree_hashes(directory)
        client.request("/api/training", expected=400)
        client.request("/api/training/round", {"request_id": "tampered-sidecar"}, expected=400)
        require(tree_hashes(directory) == before, "Coherently altered protocol sidecar was repaired or accepted")
    # Use disposable package copies to challenge actual executable bytes; never
    # mutate frozen production files, even transiently.
    for executable in ("patterns.py", "review.py", "evaluation.py"):
        directory = root / ("tamper-executable-" + executable)
        synthetic_store(directory, count=1)
        package = root / ("package-" + executable)
        shutil.copytree(ROOT / "src/gary", package / "gary", ignore=shutil.ignore_patterns("__pycache__"))
        with (package / "gary" / executable).open("a") as handle:
            handle.write("\n# Disposable independent QA byte tamper.\n")
        with server(directory, port, package=package) as (client, _):
            client.request("/api/training", expected=400)


def child_server(directory, port, fault):
    """Crash only at the OS durability boundary in an owned child process."""
    original_fsync = os.fsync
    journal = directory / "events.journal.jsonl"

    def crash_boundary(descriptor):
        opened, retained = os.fstat(descriptor), journal.stat()
        if (opened.st_dev, opened.st_ino) == (retained.st_dev, retained.st_ino):
            if fault == "before-fsync":
                os._exit(91)
            original_fsync(descriptor)
            os._exit(92)
        return original_fsync(descriptor)

    os.fsync = crash_boundary
    from gary import preview
    sys.argv = ["gary.preview", "--cycle-3", "--port", str(port), "--training-dir", str(directory)]
    preview.main()


def crash_probe(root, port):
    for fault, exit_code in (("before-fsync", 91), ("after-fsync", 92)):
        for operation in ("round", "label"):
            directory = root / ("crash-" + fault + "-" + operation)
            synthetic_store(directory, count=1)
            if operation == "label":
                with server(directory, port) as (client, _):
                    selected = client.round("crash-create")["round"]
                    card = client.card(selected, selected["order"][0])
                payload = dict(round_id=selected["round_id"], case_id=selected["order"][0], reviewer_id="gary", decision="none",
                               rationale="Disposable synthetic engineering control.", events=[], expected_revision=0,
                               revise=False, view_token=card["view_token"])
            else:
                payload = {"request_id": "crash-create"}
            with server(directory, port, fault=fault) as (client, process):
                try:
                    client.request("/api/training/" + operation, payload)
                except (RemoteDisconnected, ConnectionError, URLError):
                    pass
                else:
                    raise AssertionError("Crash injection incorrectly acknowledged the interrupted transaction")
                require(process.wait(timeout=5) == exit_code, "Owned child did not exit at the requested fsync boundary")
            with server(directory, port) as (client, _):
                recovered = client.round("crash-create")
                require(len(recovered["history"]) == 1, "Interrupted request/retry allocated a second round")
                selected = recovered["round"]
                if operation == "label":
                    acknowledged = client.request("/api/training/label", payload)
                    require(acknowledged["status"] == "complete" and acknowledged["round"]["progress"]["labeled"] == 1
                            and acknowledged["round"]["snapshot_count"] == 1, "Crash recovery lost/duplicated a retried label/snapshot")
                    fingerprint = tree_hashes(directory)
                    client.request("/api/training/label", payload)
                    require(tree_hashes(directory) == fingerprint, "Retry after recovery duplicated authoritative acknowledged work")
            with server(directory, port) as (client, _):
                recovered = client.hub()
                require(len(recovered["history"]) == 1 and recovered["round"]["round_id"] == selected["round_id"],
                        "Restart after recovery changed the allocation")
                if operation == "label":
                    require(recovered["status"] == "complete" and recovered["round"]["snapshot_count"] == 1,
                            "Restart lost acknowledged crash-recovery completion")


def legacy_probe(root, port):
    directory = root / "legacy-isolation"
    synthetic_store(directory, count=1)
    original = preservation_guard()
    with server(directory, port) as (client, _):
        legacy = client.request("/api/review?study=holdout-original")
        require(legacy["read_only"] is True and legacy["view_profile"] == "original", "Assisted exposure must keep legacy original pass read-only")
        require("diagnostic" not in legacy and "recognition" not in legacy and "predictions" not in legacy,
                "Legacy public projection changed its consensus/privacy boundary")
        # No label content is read or interpreted: only the public opaque lookup/token.
        case_id = legacy["order"][0]
        card = client.request("/api/review/card?" + urlencode({"study": "holdout-original", "id": case_id}))
        request = dict(case_id=case_id, reviewer_id="gary", decision="none", rationale="Rejected synthetic read-only control.",
                       events=[], expected_revision=0, revise=False, view_token=card["view_token"])
        client.request("/api/review/label?study=holdout-original", request, expected=403)
        selected = client.round("training-isolated")["round"]
        client.label(selected, selected["order"][0])
        require(client.request("/api/review?study=holdout-original") == legacy,
                "Train more changed legacy public progress/consensus projection")
    require(preservation_guard() == original, "Train more changed a legacy/paper artifact")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4177)
    parser.add_argument("--child-training-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--fault", choices=("before-fsync", "after-fsync"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child_training_dir:
        require(args.fault is not None, "Owned fault server requires an explicit durability fault")
        child_server(args.child_training_dir, args.port, args.fault)
        return
    baseline = preservation_guard()
    with tempfile.TemporaryDirectory(prefix="gary-training-independent-qa-") as temporary:
        for probe in (workflow_probe, admission_probe, subsequent_round_probe, tamper_probe, crash_probe, legacy_probe, exhausted_data_probe):
            started = time.monotonic()
            probe(Path(temporary), args.port)
            print(json.dumps({"probe": probe.__name__, "status": "verified", "seconds": round(time.monotonic() - started, 2)}), flush=True)
    require(preservation_guard() == baseline, "Preservation baseline changed during QA")
    print(json.dumps({"status": "verified", "preserved_files": 430, "baseline_sha256": baseline}, sort_keys=True))


if __name__ == "__main__":
    main()

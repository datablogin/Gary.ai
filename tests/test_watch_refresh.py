"""Refresh behavior at the approved add/view manual-watch boundary."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import time

from gary.watch_preview import WatchDesk
import gary.watch_preview as watch_preview


def test_corrupt_compressed_quote_finishes_refresh_and_preserves_watch_entry(tmp_path, monkeypatch):
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 9, 21, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(watch_preview, "datetime", FixedClock)
    end = datetime(2026, 10, 9, 13, 30, tzinfo=timezone.utc)
    chart = json.dumps({"chart": {"result": [{
        "meta": {"symbol": "DEMO", "currency": "USD", "instrumentType": "EQUITY"},
        "timestamp": [int((end - timedelta(days=399 - index)).timestamp()) for index in range(400)],
        "indicators": {
            "quote": [{"open": [40] * 400, "high": [41] * 400, "low": [39] * 400,
                       "close": [40] * 400, "volume": [100] * 400}],
            "adjclose": [{"adjclose": [40] * 400}],
        },
    }]}}).encode()
    # Valid gzip header, invalid deflate block: a real transport decode error.
    bad_quote = bytes.fromhex("1f8b08000000000000ff07") + b"\x00" * 8

    class SourceResponse(BytesIO):
        def __init__(self, url, raw):
            super().__init__(raw)
            self.url = url

        def geturl(self):
            return self.url

    def source_response(request, timeout):
        url = request.full_url
        return SourceResponse(url, chart if url.startswith("https://query1.finance.yahoo.com/") else bad_quote)

    monkeypatch.setattr(watch_preview, "urlopen", source_response)
    desk = WatchDesk(tmp_path / "watch", retained=tmp_path / "no-research")
    desk.add("DEMO", "Keep my research note")
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        view = desk.view()
        if view["jobs"]["DEMO"]["status"] not in {"queued", "running"}:
            break
        time.sleep(0.01)

    assert view["jobs"]["DEMO"]["status"] == "completed"
    entry = view["manual_list"][0]
    assert entry["chart_cutoff"] == "2026-10-09"
    assert "quote check failed" in entry["source_warning"]
    assert entry["checks"]["pe"]["status"] == "missing"
    assert view["buy_ready_list"] == view["radar_list"] == []
    restarted = WatchDesk(tmp_path / "watch", retained=tmp_path / "no-research").view()
    assert restarted["manual_list"][0]["note"] == "Keep my research note"

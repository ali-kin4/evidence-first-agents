"""Factual, deterministic and safe workshop scenarios with real rescanning."""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from evidence_first_agents.demo_cases import SCENARIOS, catalog
from evidence_first_agents.remediation import CONTROLS, scenario_report, simulate
from evidence_first_agents.reports import as_json
from evidence_first_agents.workbench_server import WorkbenchHandler


@pytest.mark.parametrize(
    ("key", "expected"),
    [("safe", "ready"), ("ambiguous", "warn"), ("unsafe", "fail"), ("business", "fail")],
)
def test_real_fixture_scans_match_training_labels(key, expected):
    result = scenario_report(key)
    assert result["report"]["decision"] == expected
    assert result["governance"]["decision"] == expected
    assert result["synthetic"] is True
    assert result["governance"]["assurance"] == "static-configuration-review-only"
    assert result["governance"]["runtimeTested"] is False


def test_all_demo_scans_are_deterministic():
    for key in SCENARIOS:
        assert as_json(scenario_report(key)["report"]) == as_json(scenario_report(key)["report"])


def test_unsafe_fixture_reports_secret_location_but_never_value():
    result = scenario_report("unsafe")
    codes = {f["code"] for f in result["report"]["findings"]}
    assert {"EMBEDDED_SECRET", "APPROVAL_BOUNDARY_MISSING", "WILDCARD_TOOL_SCOPE"} <= codes
    assert "FAKE_TRAINING_CREDENTIAL" not in json.dumps(result)
    assert "FAKE_TRAINING_CREDENTIAL" not in json.dumps(simulate("unsafe", []))


def test_disposable_unsafe_remediation_rescans_to_ready():
    first = scenario_report("unsafe")
    outcome = simulate("unsafe", ["environment_secret", "require_approval", "limit_tools"])
    assert first["report"]["decision"] == "fail"
    assert outcome["before"]["decision"] == "fail"
    assert outcome["after"]["decision"] == "ready"
    assert outcome["method"] == "rescan-of-disposable-fixture-copy"
    assert len(outcome["resolved"]) == 3
    assert outcome["remaining"] == []
    assert scenario_report("unsafe")["report"]["decision"] == "fail"


def test_ambiguous_remediation_requires_all_three_steps():
    partial = simulate("ambiguous", ["instruction_precedence", "mcp_transport"])
    assert partial["after"]["decision"] == "warn"
    assert "instruction_precedence" in partial["notApplicable"]
    full = simulate(
        "ambiguous", ["policy_contract", "instruction_precedence", "mcp_transport"]
    )
    assert full["after"]["decision"] == "ready"
    assert len(full["resolved"]) >= 3


def test_business_case_is_about_approval_not_simulated_failure_predictor():
    outcome = simulate("business", ["require_approval"])
    assert outcome["before"]["decision"] == "fail"
    assert outcome["after"]["decision"] == "ready"
    assert outcome["after"]["runtimeTested"] is False


def test_catalog_and_control_contracts_are_explicit():
    ids = {item["id"] for item in catalog()}
    assert ids == set(SCENARIOS)
    assert "require_approval" in CONTROLS


@pytest.mark.parametrize("selection", [["bad"], ["require_approval", "require_approval"], [{}]])
def test_unknown_or_duplicate_control_rejected(selection):
    with pytest.raises((ValueError, TypeError)):
        simulate("unsafe", selection)


@pytest.fixture
def web_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), WorkbenchHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:" + str(server.server_port)
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def request_json(root, path, data=None, headers=None):
    raw = None if data is None else json.dumps(data).encode("utf-8")
    req = Request(
        root + path, data=raw,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urlopen(req, timeout=8) as reply:
        return json.loads(reply.read())


def test_workbench_static_files_and_security_headers(web_server):
    for path, type_part in [
        ("/", "text/html"), ("/app.js", "text/javascript"),
        ("/style.css", "text/css"), ("/favicon.svg", "image/svg+xml"),
    ]:
        with urlopen(web_server + path, timeout=8) as reply:
            assert type_part in reply.headers["Content-Type"]
            csp = reply.headers["Content-Security-Policy"]
            assert "script-src 'self'" in csp
            assert "object-src 'none'" in csp
            assert len(reply.read()) > 100


def test_api_returns_fictional_evidence_and_all_scenarios(web_server):
    data = request_json(web_server, "/api/catalog")
    assert len(data["scenarios"]) == 4
    assert len(data["controls"]) == 6
    report = request_json(web_server, "/api/scenario?case=unsafe")
    assert report["report"]["decision"] == "fail"
    assert "FAKE_TRAINING_CREDENTIAL" not in json.dumps(report)


def test_api_workbench_remediation_and_export(web_server):
    selection = ["environment_secret", "require_approval", "limit_tools"]
    result = request_json(
        web_server, "/api/simulate",
        {"case": "unsafe", "controls": selection},
    )
    assert result["after"]["decision"] == "ready"
    assert result["before"]["decision"] == "fail"
    exported = request_json(web_server, "/api/export?case=unsafe")
    assert exported["synthetic"] is True
    assert exported["report"]["decision"] == "fail"


def test_api_rejects_paths_unknown_cases_and_cross_origin(web_server):
    for path in (
        "/api/scenario?case=../",
        "/api/scenario?case=/etc/passwd",
        "/api/scenario?case=unknown",
        "/../../etc/passwd",
    ):
        with pytest.raises(HTTPError) as err:
            request_json(web_server, path)
        assert err.value.code in (400, 404)
    with pytest.raises(HTTPError) as err:
        request_json(
            web_server, "/api/simulate", {"case": "safe", "controls": []},
            {"Origin": "https://invalid.example"},
        )
    assert err.value.code == 403
    with pytest.raises(HTTPError) as err:
        request_json(
            web_server, "/api/simulate", {"case": "unsafe", "controls": ["not-a-control"]}
        )
    assert err.value.code == 400

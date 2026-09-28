"""Execute the action's real Bash/Python/curl submission against a local HTTP fixture."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import yaml


root = pathlib.Path(__file__).resolve().parents[1]
action = yaml.safe_load((root / "action.yml").read_text(encoding="utf-8"))
submit = next(step for step in action["runs"]["steps"] if step.get("id") == "submit")
token = "fixture-token-never-log"
queued = {"status": "queued", "upload_id": 17, "job_id": 23}
requests = []
status, response = 202, queued


class ServiceFixture(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append((self.path, dict(self.headers), payload))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, *_args):
        pass


server = HTTPServer(("127.0.0.1", 0), ServiceFixture)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

env = {
    "PATH": f"{pathlib.Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
    "COVERAGE_UPLOAD_TOKEN": token,
    "COVERAGE_ENDPOINT": f"http://127.0.0.1:{server.server_port}/",
    "COVERAGE_PATH": "coverage/lcov.info",
    "ARTIFACT_NAME": action["inputs"]["artifact-name"]["default"],
    "ARTIFACT_ID": "123",
    "ARTIFACT_URL": "https://github.com/example/repo/actions/runs/42/artifacts/123",
    "ARTIFACT_DIGEST": "sha256:fixture-digest",
    "REPOSITORY": "example/repo",
    "HEAD_SHA": "a" * 40,
    "DEFAULT_SHA": "b" * 40,
    "HEAD_BRANCH": "feature/components",
    "REF_BRANCH": "7/merge",
    "BASE_SHA": "c" * 40,
    "BASE_BRANCH": "main",
    "PULL_REQUEST_NUMBER": "7",
    "RUN_URL": "https://github.com/example/repo/actions/runs/42",
}
legacy = {
    "commit_sha": "a" * 40,
    "branch": "feature/components",
    "base_sha": "c" * 40,
    "base_branch": "main",
    "pull_request_number": "7",
    "run_url": "https://github.com/example/repo/actions/runs/42",
    "artifact_url": "https://github.com/example/repo/actions/runs/42/artifacts/123",
    "artifact_id": "123",
    "artifact_name": "9to5-coverage",
    "artifact_digest": "sha256:fixture-digest",
    "coverage_path": "coverage/lcov.info",
}
empty_outputs = {name: "" for name in action["outputs"]}


def run(overrides, expected_payload):
    with tempfile.TemporaryDirectory() as directory:
        output = pathlib.Path(directory) / "outputs"
        output.touch()
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", submit["run"]],
            env={**env, **overrides, "GITHUB_OUTPUT": str(output), "TMPDIR": directory},
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert token not in result.stdout + result.stderr, "token leaked to logs"
        assert not (pathlib.Path(directory) / "injected").exists(), "shell input executed"
        path, headers, payload = requests.pop(0)
        assert path == "/api/v1/repos/example/repo/coverage", path
        assert headers["Authorization"] == f"Bearer {token}"
        assert headers["Content-Type"] == "application/json"
        assert payload == expected_payload, (payload, expected_payload)
        outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
        if status >= 400:
            assert result.returncode != 0, "HTTP rejection must fail the action"
            assert outputs == {}, outputs
        else:
            assert result.returncode == 0, result.stderr
        return payload, outputs


try:
    for overrides in ({}, {"COVERAGE_COMPONENT": ""}):
        _, outputs = run(overrides, legacy)
        assert outputs == empty_outputs, outputs

    for component in ("shared-library-42", " API ", 'quotes"\\\n$(touch injected)`touch injected`é'):
        _, outputs = run({"COVERAGE_COMPONENT": component}, {**legacy, "component": component})
        assert outputs == empty_outputs, outputs

    # Two independent jobs target the PR head with separate artifacts and components.
    uploads = []
    for component, artifact_id in (("api", "124"), ("website", "125")):
        artifact_url = f"https://github.com/example/repo/actions/runs/42/artifacts/{artifact_id}"
        payload, outputs = run(
            {
                "COVERAGE_COMPONENT": component,
                "ARTIFACT_NAME": f"coverage-{component}",
                "ARTIFACT_ID": artifact_id,
                "ARTIFACT_URL": artifact_url,
            },
            {
                **legacy,
                "component": component,
                "artifact_name": f"coverage-{component}",
                "artifact_id": artifact_id,
                "artifact_url": artifact_url,
            },
        )
        assert outputs == empty_outputs, outputs
        uploads.append(payload)
    assert uploads[0]["commit_sha"] == uploads[1]["commit_sha"] == env["HEAD_SHA"]
    assert uploads[0]["artifact_name"] != uploads[1]["artifact_name"]

    run(
        {"HEAD_SHA": "", "HEAD_BRANCH": "", "REF_BRANCH": "main", "BASE_SHA": "", "PULL_REQUEST_NUMBER": ""},
        {**legacy, "commit_sha": "b" * 40, "branch": "main", "base_sha": "", "pull_request_number": ""},
    )

    for status, code in ((401, "invalid_token"), (422, "invalid_component"), (422, "invalid_configuration"), (500, "internal_error")):
        response = {"error": code}
        run({"COVERAGE_COMPONENT": "unknown"}, {**legacy, "component": "unknown"})

    status = 200
    response = {
        "coverage_run_id": 19,
        "project_coverage": 87.5,
        "patch_coverage": 0,
        "project_conclusion": "success",
        "patch_conclusion": "failure",
    }
    _, outputs = run({}, legacy)
    assert outputs == {
        "coverage-run-id": "19",
        "project-coverage": "87.5",
        "patch-coverage": "0",
        "project-conclusion": "success",
        "patch-conclusion": "failure",
    }, outputs
finally:
    server.shutdown()
    server.server_close()
    thread.join()

print("Submission contract passed: legacy, component serialization, independent uploads, queued outputs, and HTTP failures.")

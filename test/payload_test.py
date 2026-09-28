"""Exercise the actual embedded payload producer without network uploads."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import yaml


ACTION = yaml.safe_load((pathlib.Path(__file__).parents[1] / "action.yml").read_text())
STEP = next(step for step in ACTION["runs"]["steps"] if step.get("id") == "submit")
CODE = STEP["run"].split("<<'PY'\n", 1)[1].split("\nPY", 1)[0]
HEAD = "a" * 40
BASE = "b" * 40


class PayloadTest(unittest.TestCase):
    def payload(self, changes=None, checkout=HEAD):
        env = dict(REPORT_SCOPE="ios", EVENT_NAME="pull_request", DEFAULT_BRANCH="main",
                   HEAD_SHA=HEAD, DEFAULT_SHA="c" * 40, HEAD_BRANCH="feature", REF_BRANCH="21/merge",
                   BASE_SHA=BASE, BASE_BRANCH="main", PULL_REQUEST_NUMBER="21", RUN_URL="https://github.test/run",
                   ARTIFACT_URL="https://github.test/artifact", ARTIFACT_ID="1", ARTIFACT_NAME="coverage",
                   ARTIFACT_DIGEST="sha256:test", COVERAGE_PATH="coverage/lcov.info")
        env.update(changes or {})
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "payload.json"
            with patch.dict(os.environ, env, clear=True), patch("sys.argv", ["producer", str(output)]), \
                    patch("subprocess.check_output", return_value=checkout + "\n"):
                exec(compile(CODE, "action.yml:payload", "exec"), {})
            return json.loads(output.read_text())

    def test_pr_head_and_scope(self):
        for scope in ("ios", "android"):
            payload = self.payload({"REPORT_SCOPE": scope})
            self.assertEqual((HEAD, BASE, "feature", "main", "21", scope),
                             tuple(payload[k] for k in ("commit_sha", "base_sha", "branch", "base_branch", "pull_request_number", "report_scope")))

    def test_main_and_manual_baseline(self):
        for event in ("push", "workflow_dispatch"):
            payload = self.payload(dict(EVENT_NAME=event, HEAD_SHA="", DEFAULT_SHA=HEAD,
                                        HEAD_BRANCH="", REF_BRANCH="main", BASE_SHA="", PULL_REQUEST_NUMBER=""))
            self.assertEqual(HEAD, payload["commit_sha"])
            self.assertEqual("main", payload["branch"])

    def test_missing_pr_fields_and_wrong_checkout_fail(self):
        for key in ("HEAD_SHA", "HEAD_BRANCH", "BASE_SHA", "BASE_BRANCH", "PULL_REQUEST_NUMBER"):
            with self.assertRaisesRegex(SystemExit, "Missing PR"):
                self.payload({key: ""})
        with self.assertRaisesRegex(SystemExit, "checkout differs"):
            self.payload(checkout="c" * 40)

    def test_invalid_scope_sha_and_manual_feature_fail(self):
        for change in ({"REPORT_SCOPE": "other"}, {"HEAD_SHA": "bad"}, {"BASE_SHA": "bad"}, {"PULL_REQUEST_NUMBER": "0"},
                       {"EVENT_NAME": "workflow_dispatch", "PULL_REQUEST_NUMBER": ""}):
            with self.assertRaises(SystemExit):
                self.payload(change)

    def test_legacy_payload_has_no_scope(self):
        self.assertNotIn("report_scope", self.payload({"REPORT_SCOPE": ""}, checkout="c" * 40))


if __name__ == "__main__":
    unittest.main()

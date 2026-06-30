import pathlib

import yaml


def assert_equal(expected, actual, message):
    if expected != actual:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def assert_includes(value, substring, message):
    if substring not in value:
        raise AssertionError(f"{message}: {substring!r} missing")


action_path = pathlib.Path(__file__).resolve().parents[1] / "action.yml"
with action_path.open(encoding="utf-8") as handle:
    action = yaml.safe_load(handle)

inputs = action["inputs"]
endpoint = inputs["endpoint"]

assert_equal(False, endpoint["required"], "endpoint should be optional")
assert_equal("https://coverage.9to5.software/", endpoint["default"], "endpoint default")
assert_equal(True, inputs["token"]["required"], "token should be required")
assert_equal(True, inputs["path"]["required"], "path should be required")

upload_step = next(
    (step for step in action["runs"]["steps"] if step.get("id") == "upload"),
    None,
)
if upload_step is None:
    raise AssertionError("upload step exists")

assert_equal("actions/upload-artifact@v7", upload_step["uses"], "upload artifact action")
assert_equal("error", upload_step["with"]["if-no-files-found"], "missing files behavior")

submit_step = next(
    (step for step in action["runs"]["steps"] if step.get("id") == "submit"),
    None,
)
if submit_step is None:
    raise AssertionError("submit step exists")

assert_equal(
    "${{ inputs.endpoint }}",
    submit_step["env"]["COVERAGE_ENDPOINT"],
    "submit endpoint env",
)
assert_includes(
    submit_step["run"],
    'endpoint="${COVERAGE_ENDPOINT%/}"',
    "submit trims endpoint",
)
assert_includes(
    submit_step["run"],
    "${endpoint}/api/v1/repos/${REPOSITORY}/coverage",
    "submit route",
)

for name, output in action["outputs"].items():
    assert_equal(
        f"${{{{ steps.submit.outputs.{name} }}}}",
        output["value"],
        f"{name} output wiring",
    )

print("Action metadata contract passed.")

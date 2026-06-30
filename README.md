# 9to5 Coverage Action

Upload an LCOV or Cobertura coverage file as a GitHub Actions artifact, then submit that artifact URL to 9to5 Coverage for processing.

## Usage

Store your 9to5 Coverage upload token as `COVERAGE_UPLOAD_TOKEN`.

```yaml
name: coverage

on:
  pull_request:
  push:

jobs:
  coverage:
    if: github.event_name == 'pull_request' || github.ref_name == github.event.repository.default_branch
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test -- --coverage --coverageReporters=lcov
      - name: Upload coverage
        uses: 9to5/9to5-coverage-action@v1
        with:
          token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
          path: coverage/lcov.info
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `token` | yes | | 9to5 Coverage upload token. |
| `path` | yes | | Path to the LCOV or Cobertura file. |
| `endpoint` | no | `https://coverage.9to5.software/` | Base URL for the 9to5 Coverage app. |
| `artifact-name` | no | `9to5-coverage` | Name for the GitHub Actions artifact. |
| `retention-days` | no | `7` | Number of days GitHub should retain the artifact. |

## Outputs

| Output | Description |
| --- | --- |
| `coverage-run-id` | 9to5 Coverage run ID. |
| `project-coverage` | Project coverage percentage. |
| `patch-coverage` | Patch coverage percentage. |
| `project-conclusion` | Project coverage conclusion. |
| `patch-conclusion` | Patch coverage conclusion. |

## Language Examples

JavaScript and TypeScript:

```yaml
- run: npm test -- --coverage --coverageReporters=lcov
- name: Upload coverage
  uses: 9to5/9to5-coverage-action@v1
  with:
    token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
    path: coverage/lcov.info
```

Python:

```yaml
- run: pytest --cov=src --cov-report=xml:coverage.xml
- name: Upload coverage
  uses: 9to5/9to5-coverage-action@v1
  with:
    token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
    path: coverage.xml
```

Java:

```yaml
- run: mvn -B test jacoco:report
- run: reportgenerator "-reports:target/site/jacoco/jacoco.xml" "-targetdir:coverage" "-reporttypes:Cobertura"
- name: Upload coverage
  uses: 9to5/9to5-coverage-action@v1
  with:
    token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
    path: coverage/Cobertura.xml
```

PHP:

```yaml
- run: vendor/bin/phpunit --coverage-cobertura coverage/cobertura.xml
- name: Upload coverage
  uses: 9to5/9to5-coverage-action@v1
  with:
    token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
    path: coverage/cobertura.xml
```

Go:

```yaml
- run: go test ./... -coverprofile=coverage.out
- run: gcov2lcov -infile=coverage.out -outfile=coverage.lcov
- name: Upload coverage
  uses: 9to5/9to5-coverage-action@v1
  with:
    token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
    path: coverage.lcov
```

## What The Action Sends

The action uploads your coverage file with `actions/upload-artifact@v7`, then submits the artifact URL, artifact ID, digest, run URL, commit SHA, branch, base branch, base SHA, and pull request number to 9to5 Coverage.

9to5 Coverage downloads the artifact through the installed GitHub App and processes the coverage file server-side.

## Troubleshooting

- `Coverage file not found`: confirm the coverage command writes the file at the path passed to `path`.
- `401 invalid upload token`: rotate the repository or organization token in 9to5 Coverage and update `COVERAGE_UPLOAD_TOKEN`.
- `artifact_url must belong to the requested repository`: confirm the workflow runs in the repository connected to 9to5 Coverage.
- `coverage file was not found in the artifact`: confirm `path` points to the generated LCOV or Cobertura file.

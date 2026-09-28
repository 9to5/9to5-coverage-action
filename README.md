# 9to5 coverage Action

Upload an LCOV or Cobertura coverage file as a GitHub Actions artifact, then submit that artifact URL to 9to5 coverage for processing.

Homepage: [9to5 coverage](https://coverage.9to5.software)

## Usage

Store your 9to5 coverage upload token as `COVERAGE_UPLOAD_TOKEN`.

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
      - uses: actions/checkout@v7
      - run: npm ci
      - run: npm test -- --coverage --coverageReporters=lcov
      - name: Upload coverage
        uses: 9to5/9to5-coverage-action@v1
        with:
          token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
          path: coverage/lcov.info
```

## Inputs

| Input            | Required | Default                           | Description                                       |
| ---------------- | -------- | --------------------------------- | ------------------------------------------------- |
| `token`          | yes      |                                   | 9to5 coverage upload token.                       |
| `path`           | yes      |                                   | Path to the LCOV or Cobertura file.               |
| `component`      | no       |                                   | Repository-defined component ID; omitted from the payload when empty. |
| `endpoint`       | no       | `https://coverage.9to5.software/` | Base URL for the 9to5 coverage app.               |
| `artifact-name`  | no       | `9to5-coverage`                   | Name for the GitHub Actions artifact.             |
| `retention-days` | no       | `7`                               | Number of days GitHub should retain the artifact. |

## Outputs

| Output               | Description                  |
| -------------------- | ---------------------------- |
| `coverage-run-id`    | 9to5 coverage run ID.        |
| `project-coverage`   | Project coverage percentage. |
| `patch-coverage`     | Patch coverage percentage.   |
| `project-conclusion` | Project coverage conclusion. |
| `patch-conclusion`   | Patch coverage conclusion.   |

Artifact submissions are asynchronous. A successful `status: queued` response means the upload was accepted for processing; it does **not** mean project or patch coverage passed. Outputs absent from the response remain empty, including percentages, conclusions, and the coverage run ID. Check processing status on the repository page and the service's GitHub checks. This action does not poll for results.

## Monorepositories

**Release prerequisite:** component uploads require the service implementation in [9to5-coverage#79](https://github.com/9to5/9to5-coverage/issues/79). Do not publish a component-capable action release or move the `v1` tag until that API is available. The examples below describe that capability; use an action version that includes it.

Define components in `.9to5-coverage.json` at the repository root. For example, two independent components could be:

```json
{
  "version": 1,
  "components": {
    "api": {"root": "services/api", "path_prefix": "services/api"},
    "website": {"root": "apps/website", "path_prefix": "apps/website"}
  }
}
```

The names, roots, and component count belong to your repository. These names are examples, not built-in choices. The service reads configuration at the exact uploaded commit and validates each `component`; the action forwards the identifier unchanged. Omit `component` for repositories without this configuration.

The following illustrative workflow runs both jobs independently for the same push or pull request head SHA. Replace the test commands with your suites. This example assumes each report contains paths relative to its component directory, such as `src/index.ts`; `path_prefix` maps them to repository-relative source paths. Omit `path_prefix` if your reports already contain repository-relative paths.

```yaml
name: component coverage

on:
  pull_request:
  push:

jobs:
  coverage:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - component: api
            directory: services/api
            artifact: coverage-api
          - component: website
            directory: apps/website
            artifact: coverage-website
    steps:
      - uses: actions/checkout@v7
      - run: npm ci
        working-directory: ${{ matrix.directory }}
      - run: npm test -- --coverage --coverageReporters=lcov
        working-directory: ${{ matrix.directory }}
      - name: Upload component coverage
        uses: 9to5/9to5-coverage-action@v1
        with:
          token: ${{ secrets.COVERAGE_UPLOAD_TOKEN }}
          path: ${{ matrix.directory }}/coverage/lcov.info
          component: ${{ matrix.component }}
          artifact-name: ${{ matrix.artifact }}
```

Give every component job a distinct `artifact-name`, such as `coverage-api` and `coverage-website`, to avoid collisions within a workflow run. The default remains `9to5-coverage` for ordinary usage. Components may arrive in either order; the service owns aggregation and completeness.

The initial configured commit needs fresh reports for **all** components. Later, only the service can verify whether an unchanged component's earlier measurement can be carried forward. Changes to declared dependencies require fresh dependant reports; changes outside component roots or to configuration can require all reports. A missing or failed job is never evidence that reuse is safe. Carry-forward does not mean tests ran on the current commit. This action does not detect affected paths, skip jobs, or parse configuration.

See the [service API documentation](https://coverage.9to5.software/docs#api-reference) for response semantics. Generic configuration, the mobile/shared-library dependency example, path rules, and carry-forward requirements are specified in the [service component contract](https://github.com/9to5/9to5-coverage/issues/79); its public monorepository documentation is part of that pending service delivery.

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

The action uploads your coverage file with `actions/upload-artifact@v7`, then submits the artifact URL, artifact ID, digest, run URL, commit SHA, branch, base branch, base SHA, and pull request number to 9to5 coverage.

When `component` is non-empty, the JSON request also includes that exact value. An omitted or empty input leaves the existing payload unchanged.

9to5 coverage downloads the artifact through the installed GitHub App and processes the coverage file server-side.

## Troubleshooting

- `Coverage file not found`: confirm the coverage command writes the file at the path passed to `path`.
- `401 invalid upload token`: rotate the repository or organization token in 9to5 coverage and update `COVERAGE_UPLOAD_TOKEN`.
- `artifact_url must belong to the requested repository`: confirm the workflow runs in the repository connected to 9to5 coverage.
- `coverage file was not found in the artifact`: confirm `path` points to the generated LCOV or Cobertura file.
- Artifact name conflict: set a distinct `artifact-name` for each component job in the workflow run.
- `422` component/configuration rejection: check that the ID matches `.9to5-coverage.json` at the uploaded SHA, or omit it for an ordinary repository. The action fails on HTTP errors; it does not silently retry as a whole-repository upload.
- Accepted upload but missing metrics: `queued` means processing is pending. Inspect the repository page and GitHub checks for processing failures or missing component reports; empty outputs are not passing coverage results.

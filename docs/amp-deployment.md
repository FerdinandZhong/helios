# Standalone Helios AMP

Updated 5 November 2026. This AMP runs native Helios in its own CAI project.
One authenticated Application serves both the React UI and the native API.
Semantic Hub remains a separate project and connects through the Application URL.

```text
Helios AMP -> setup job -> authenticated Helios Application
                                  |
                       +----------+-----------+
                       |                      |
                  Native UI               Native API
                       |                      |
                       +--- same origin ------+
                                              |
                                  Native state and data sources
```

## Launch in Cloudera AI

1. Import this Helios repository revision as an AMP using the root `.project-metadata.yaml`.
2. Select Standard JupyterLab Python 3.12 for setup and Application.
3. Retain `/home/cdsw/state/helios.db` as the metadata path, or specify your existing absolute path.
4. Keep `HELIOS_SQLITE_JOURNAL_MODE=DELETE` for the shared project filesystem.
5. Wait for `helios-amp-setup` to finish and the `Helios` Application to start.
6. Open the assigned HTTPS Application URL.
7. Grant native organization access with the explicit administrator command below.
8. Configure native data sources, inference, and MCP before testing semantic building or chat.

The manifest creates a setup job, runs it to completion, then starts one authenticated Application.
Setup uses 2 CPUs and 8 GB memory; the Application uses 2 CPUs and 8 GB memory.
No GPU, custom runtime, application-management key, or manually assigned API origin is required for installation.
Package installation requires Python/npm registry access and access to the official Node download host.
The AMP does not deploy an MCP service or provision warehouse credentials.

## Runtime and connection settings

| Item | Value |
| --- | --- |
| Setup script | `cai_amp/setup.py` |
| Application script | `cai_amp/launch.py` |
| Isolated environment | `.venv-helios-amp` |
| UI and API origin | The same assigned HTTPS Application URL |
| UI health | `/healthz` |
| API and metadata health | `/api/v1/healthz` |
| Native documentation UI | `/docs` |
| API Swagger | `/api/docs` |
| API schema | `/api/openapi.json` or `/openapi.json` |

The launcher preserves the Workbench kernel and supervises a separate server process.
The server listens only on `127.0.0.1:$CDSW_APP_PORT` in CAI.
The gateway supplies identity; the wrapper passes headers to native Helios without creating an identity or sharing a service key.
The API retains native authorization and grants.
The CAI launcher rejects `HELIOS_DEV` and `HELIOS_DEV_USER`.
Never enable unauthenticated Application access.

The browser receives `window.location.origin` as its API URL.
`HELIOS_API_URL` and `HELIOS_UI_ORIGINS` are unnecessary for this combined deployment.
No proxy forwards API requests between applications, so the native API sees its original `/api/v1/...` paths.
The [two-Application deployment](ui-deployment.md) remains available for installations that require separate UI and API processes.

## Native organization access

Installation creates no users, grants, sample models, or published releases.
An administrator must supply the exact `remote-user` value from the signed-in user's CAI identity.
An authenticated user without native grants can open the UI but sees no authorized workspace.

Run from the project root in a Workbench session:

```bash
.venv-helios-amp/bin/python -I cai_amp/admin.py \
  --username YOUR_CAI_USERNAME \
  --organization finance \
  --name 'Finance analytics'
```

This explicit command creates the organization only if it does not exist and grants that user native `org_admin` membership.
Rerunning the command preserves the existing organization name and does not create a model or publish a release.
Use the native UI to create a model and configure its sources.
Use upstream's `helios_core.metadata.users` tooling for subsequent model grants.

## Setup details and dependency boundaries

The API installs from `cai_amp/requirements.lock` into a virtual environment without notebook package inheritance.
The lock derives from the upstream API baseline and includes its missing native dependencies:

- `rapidfuzz==3.14.6` for crawler matching.
- `linkml-runtime==1.12.1` for ontology imports.
- `jsonschema==4.26.0` to satisfy the LinkML runtime requirements.

These are packaging dependencies. The AMP does not alter upstream API or UI application code.
Optional `lancedb` and `sentence-transformers` are not installed by this baseline.
Document embedding and vector evidence search require a separately reviewed dependency extension.
Native building and chat still require their configured inference, MCP, sources, and grants.

Setup downloads Node.js 22.23.3 into `.amp-tools` and checks the archive against pinned official SHA-256 values.
It supports Linux x64/arm64 and macOS x64/arm64 for local rehearsal.
It uses `npm ci` and the existing UI package lock, then builds the production UI.
Restarting the Application does not reinstall packages or rebuild assets.
The installer verifies native imports and database migrations against disposable state before reporting success.

Retain native metadata, `runs/`, `models/`, uploaded artifacts, and application configuration during upgrades.
Stop native writers and back up state before upgrading an existing installation.
The API performs its normal native schema migration at startup.
Setup itself does not migrate the production database or reset state.

## Connect Semantic Hub

1. Copy the exact Helios Application HTTPS origin.
2. Set Hub `HELIOS_UI_ORIGIN` and `HELIOS_API_ORIGIN` to that same origin.
3. Set `HELIOS_HEALTH_API_KEY` if authenticated CAI ingress requires a credential for server health checks.
4. Restart Hub in `auto` mode or run its documented connection retry.
5. Confirm registration, then link a workspace using the caller's native permissions.

Hub provider registration checks `/healthz` and `/api/v1/healthz`.
It does not prove native model-query readiness or replace native authorization.

## Local rehearsal

Run setup with Python 3.12 from the repository root:

```bash
python3.12 cai_amp/setup.py
HELIOS_METADATA_DB=/tmp/helios-amp-review.db \
  .venv-helios-amp/bin/python -I cai_amp/server.py --local --port 8310
```

Local mode binds loopback and does not supply a fake user automatically.
For a local identity test, use a disposable database and explicit fixture headers or upstream's development settings.
Never use those settings to establish CAI authentication acceptance.

## Verification and live-test gate

Upstream `Christopheraburns/helios` main was fetched again on 5 November 2026 at `72818c4`.
The AMP branch contains that commit; no later upstream application changes were available.

The local rehearsal installed the Python 3.12 environment, passed `pip check`, built the UI, and verified native imports and metadata migration.
All 13 packaging tests passed, covering manifest sequencing, API identity, streaming, route isolation, SPA routing, asset caching, startup guards, child failure, and archive checksum failure.
The native API/UI local health checks passed.
Browser checks passed for home, models, native documentation, same-origin configuration, Swagger, and the absence of page errors.
Local fixture checks confirmed anonymous diagnostics rejection, native identity/grants, and repeated admin setup preserving the organization name.
These fixture headers were used only on loopback; they do not establish CAI identity verification.
The dependency build reported 14 upstream npm advisories, including one critical advisory; no automatic dependency upgrades were applied.
Large UI bundle warnings also remain from the upstream build.

Before declaring live AMP acceptance:

1. Complete a fresh CAI import and retain setup logs and the exact source commit.
2. Verify both health endpoints and the native UI through authenticated ingress.
3. Confirm anonymous requests cannot reach protected API resources.
4. Verify native diagnostics and workspace discovery with two differently authorized users.
5. Restart the Application and confirm metadata, grants, and model artifacts persist.
6. Configure inference, MCP, and a source; complete one native build and one native query.
7. Register the provider from the separate Semantic Hub project.

Local success does not establish CAI ingress behavior, warehouse connectivity, or model inference.

## References

- [Cloudera AMP specification](https://docs.cloudera.com/machine-learning/cloud/applied-ml-prototypes/ml-amp.pdf)
- [Pinned Node archive checksums](https://nodejs.org/download/release/v22.23.3/SHASUMS256.txt)
- [Native UI/API networking](ui-api-networking.md)
- [Native metadata operations](helios-metadata-database.md)

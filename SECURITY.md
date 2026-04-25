# Security Policy

## Supported Versions

Security fixes are provided for the current `main` branch and the latest published container image tag.

Pinned dependencies are refreshed through repository updates and image rebuilds. Older image tags are retained for traceability but are not actively patched; upgrade to the newest published image when a security fix is released.

## Reporting a Vulnerability

Please do not report suspected vulnerabilities in public GitHub issues or discussions.

Use GitHub private vulnerability reporting for this repository when available. If that is not available, email the maintainer at <ms7322@columbia.edu> with enough detail to reproduce and assess the issue.

Include, when possible:

- The affected image tag, commit, or branch
- The affected component, package, or configuration path
- Steps to reproduce or a proof of concept
- Expected impact and any known mitigations
- Whether the report is under active disclosure elsewhere

You should receive an initial acknowledgement within 7 days. The maintainer will investigate, coordinate any required fix, and publish remediation guidance or a patched image when appropriate.

## Scope

This policy covers vulnerabilities in this repository's Docker image, Compose configuration, Makefile automation, CI workflows, and pinned runtime dependencies.

This policy does not cover vulnerabilities in local notebooks, datasets, files under `workspace/`, local `.env` files, host Docker installations, GPU drivers, or other user-managed host configuration.

## Security Expectations

- Keep `JUPYTER_TOKEN` private and do not commit `.env` files.
- Bind Jupyter to `127.0.0.1` unless you have intentionally secured network exposure.
- Pull or rebuild the image regularly to receive dependency updates.
- Run `make validate` when Docker Scout is available to review image vulnerability findings.

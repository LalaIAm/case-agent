# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.

## Dependency Auditing

This repository runs automated dependency audits for Python and Node.js:

- **Python**: `pip-audit -r backend/requirements.txt`
- **Node.js**: `npm audit --audit-level=high --package-lock-only` in `frontend/`

These checks run on pull requests and on a scheduled basis. Any high/critical
findings should be addressed before merging changes.

## Lockfile Review Policy

Lockfile updates must be reviewed with extra care:

- Verify newly introduced packages are expected and have legitimate sources.
- Confirm version bumps align with the intended dependency updates.
- For automated updates (Dependabot), review the audit results and release
  notes for the updated packages.

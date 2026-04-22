# Security Policy

## Supported versions

Only the latest minor version of the latest major version receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a vulnerability

Please report security issues via GitHub's private security advisory:

- Navigate to https://github.com/yaniv-golan/offlickr/security/advisories/new
- Provide: affected versions, reproduction steps, impact, any suggested remediation.

We aim to acknowledge reports within **7 days** and publish a fix or mitigation within **30 days** for critical issues.

Please do **not** file public GitHub issues for security problems.

## Yank policy

If a released version is found to contain a security or correctness regression serious enough to withdraw, we yank it on PyPI (`pip install offlickr==X.Y.Z` will still work for pinned installs but it is hidden from resolvers). We also annotate the corresponding GitHub Release and release-notes file with a `**YANKED YYYY-MM-DD** — reason` header. We do not delete published Git tags or GitHub Releases.

## What `offlickr` does not do

- It does not transmit your Flickr data anywhere. All processing is local.
- External asset fetching (optional) talks only to `api.flickr.com` and `live.staticflickr.com` / `farm*.staticflickr.com`, and only when explicitly enabled.
- Archived content may contain personally identifying information (real names, locations, tagged users) in comments and descriptions from other Flickr users. HTML is sanitized, but PII inside text cannot be. Review your archive before sharing or publishing it.

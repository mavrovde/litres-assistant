# Security Policy

## Supported Versions

This is a small, personal, single-maintainer tool with no formal release
branches -- only the latest commit on `main` is supported. There are no
older versions receiving security fixes.

## Reporting a Vulnerability

Please open a [GitHub issue](https://github.com/mavrovde/litres-assistant/issues)
describing the problem. Since this runs entirely locally (bound to
`127.0.0.1`, no server-side component, no telemetry -- see the README's
"Security notes"), the realistic attack surface is limited to the local
machine it runs on and the app's own dependencies; please call that context
out if it's relevant to what you found.

There's no bug bounty or guaranteed response time -- this is maintained on
a best-effort basis.

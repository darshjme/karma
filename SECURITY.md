# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, email **security@your-org.example** with:

1. A description of the vulnerability.
2. Steps to reproduce.
3. Potential impact.
4. Any suggested mitigations.

We will acknowledge receipt within **48 hours** and aim to release a fix within **14 days** for critical issues.

## Scope

- Arbitrary code execution via crafted workflow definitions.
- Dependency injection attacks through the `context` dict.
- Thread-safety issues in parallel task execution.

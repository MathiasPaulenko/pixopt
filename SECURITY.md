# Security Policy

## Supported Versions

We release security updates for the currently supported minor versions of `pixopt`:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security issue in `pixopt`, please report it privately.

- **Email**: [security@mathiaspaulenko.dev](mailto:security@mathiaspaulenko.dev) (or open a private security advisory on GitHub if enabled)
- **Do not** open a public issue for security vulnerabilities.

Please include:

- A description of the vulnerability
- Steps to reproduce it
- Affected versions
- Any suggested remediation

We aim to acknowledge reports within 48 hours and provide a resolution or timeline within 7 days.

## Security Best Practices

When using `pixopt`:

- Do not expose the CLI or API to untrusted input without validation.
- Be cautious when optimizing user-provided SVG files; the optimizer does not sanitize arbitrary HTML/JS inside SVGs.
- Review output paths and backup settings when running in production environments.

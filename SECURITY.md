# Security Policy

## Reporting a Vulnerability

**Please do not post security issues in public issues or Discussions.**

If you discover a security vulnerability, please report it privately:

- **Email:** thales.mms (at) proton.me
- **Encrypted channel for sensitive details:** Signal is preferred; Telegram secret chat is available
  if needed. Send a brief email requesting an encrypted channel and include only non-sensitive contact
  details in that initial email.

Do not send proof-of-concept data, patient information, screenshots, logs, or sensitive attachments in
plain email. If you need to use encrypted email, request a PGP/GPG public key and fingerprint first,
then encrypt sensitive attachments with that key before sending them.

In your report, include:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any mitigations you can suggest

We will respond within 48 hours and keep you updated during remediation.

## Scope

Security reports are welcome for:

- The plugin itself (macOS application code)
- The bundled Python script and its dependencies
- Build and release scripts

**Not in scope:**

- Third-party frameworks (Horos SDK, OsiriX SDK)
- macOS OS vulnerabilities
- Network/transport issues unrelated to the plugin

## What We Do

- Investigate and validate the report
- Release a fix or mitigation when ready
- Acknowledge contributors when appropriate

Thank you for helping keep this project secure.

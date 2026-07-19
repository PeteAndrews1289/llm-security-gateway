# Security Policy

## Supported scope

Security reports are accepted for the current `main` branch, including the Lambda handler and filters, packaging script, Terraform configuration, and tests. Historical commits, deleted branches, forks, AWS, OpenAI services, and other third-party dependencies are outside the supported scope.

This is a completed, dismantled demonstration lab. There is no live gateway, cloud infrastructure, model endpoint, or credential associated with this repository. The application under `vulnerable_app/` is intentionally insecure and uses mock data; its documented behavior is not itself a vulnerability unless it causes an unintended impact outside that stated scope.

## Reporting a vulnerability

Use GitHub's **Security > Advisories > Report a vulnerability** flow for this repository. Please include:

- the affected file and current commit;
- a concise description of the impact;
- safe, minimal reproduction steps using mock data; and
- a suggested remediation, if available.

Do not open a public issue for a suspected vulnerability, secret, credential, prompt content containing real private data, or other sensitive information. Do not test old endpoints or keys found in history. Use only systems you own and control, avoid destructive or cost-generating tests, and stop if testing could affect another person or service.

Reports are reviewed on a best-effort basis. This portfolio project does not promise a response or remediation timeframe.

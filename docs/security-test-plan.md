# LLM Security Test Plan

This test plan documents the security behaviors validated by the LLM gateway lab.

## Scope

- Baseline direct LLM access
- AWS API Gateway and Lambda proxy
- Input prompt injection filtering
- Output DLP redaction
- API Gateway throttling

## Test Case 1: Baseline Refusal

Goal: confirm that a direct LLM call refuses a simple request for the mock secret.

Expected result:

- The model refuses or avoids revealing the mock secret.
- The result establishes a baseline before adding gateway controls.

## Test Case 2: Contextual Prompt Injection

Goal: show that relying only on a system prompt is not sufficient.

Expected result:

- A contextual or roleplay-style prompt attempts to bypass the instruction boundary.
- The result demonstrates why external controls are needed.

## Test Case 3: Input Firewall Block

Goal: confirm the Lambda input scanner blocks known prompt injection phrases and patterns.

Expected result:

- API returns HTTP 403.
- The request is not sent to the LLM provider.
- The blocked request is visible in Lambda logs.

## Test Case 4: Output DLP Redaction

Goal: confirm the outbound filter redacts sensitive strings if the LLM response contains them.

Expected result:

- Raw sensitive text is replaced with `[REDACTED_BY_DLP_FIREWALL]`.
- The user receives a sanitized response.
- The DLP event is visible in Lambda logs.

## Test Case 5: Rate Limiting

Goal: confirm API Gateway throttling reduces burst abuse and denial-of-wallet risk.

Expected result:

- Excessive requests receive HTTP 429 after throttling is active.
- Normal request volume continues to work.

## Security Notes

- Input filtering is not a complete prompt injection solution.
- Output redaction is a safety net, not a replacement for good data handling.
- Sensitive values should be stored in a managed secret store for production use.
- Production systems should add authentication, structured logging, monitoring, and alerting.

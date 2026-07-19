# Evidence and Limitations

## Observed

- A direct-to-model baseline disclosed a mock secret under a role-play prompt.
- The deployed API Gateway and Lambda path returned successful responses.
- The demo keyword filter returned HTTP 403 for one known prompt pattern.
- The known-pattern output filter replaced the lab's mock secret before returning it.
- API Gateway route throttling was configured in Terraform.

## What this does not prove

- A keyword list is not comprehensive prompt-injection prevention.
- A regex for one mock-secret family is not general-purpose data loss prevention.
- Throttling without authentication, quotas, monitoring, and budget controls is not complete denial-of-wallet protection.
- The evidence set is a handful of manually selected cases, not a measured adversarial evaluation.

## Portfolio hygiene

The original proxy screenshot displayed a revoked OpenAI API key and was removed from the current branch. Packaged third-party dependencies and compiled binaries were also removed; the Lambda bundle is now generated from a pinned dependency file. Git history remains available to the repository owner.

## Next validation step

Create a labeled adversarial corpus covering benign prompts, paraphrases, Unicode, encoding, multilingual inputs, indirect injection, and extraction attempts. Publish pass rates and false positives before making stronger security claims.

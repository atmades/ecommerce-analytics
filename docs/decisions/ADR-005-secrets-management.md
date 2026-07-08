# ADR-005: GCP Secret Manager for Credentials

**Status:** Accepted  
**Date:** 2026-06

## Context

The project requires storing multiple credentials:
- GCP Service Account key
- MercadoLibre client_id / client_secret
- Gemini API key (optional)
- Slack webhook (planned)

These must never appear in code, git history, or environment files committed to version control.

## Decision

Use **GCP Secret Manager** for all credentials at runtime.
Use **Workload Identity Federation** for GitHub Actions (no static keys).

```python
from google.cloud import secretmanager

def get_secret(secret_id: str, project_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

## Consequences

**Positive:**
- Zero secrets in code or git history
- Access audit log — every secret access is logged
- Rotation support — update secret without changing code
- IAM-controlled access — only authorized service accounts can read

**Negative:**
- Requires GCP setup — barrier for new contributors
- Network call on each secret access (mitigated by `@lru_cache`)
- Local development requires service account key file (acceptable tradeoff)

## Alternatives Considered

**`.env` files:** Simple but risky — easy to accidentally commit. No audit trail, no rotation.

**GitHub Actions Secrets:** Good for CI/CD only. Not accessible at runtime in Airflow or Python scripts.

**HashiCorp Vault:** More powerful but significant operational overhead. Overkill for single-project use.
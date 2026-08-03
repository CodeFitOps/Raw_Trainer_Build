# src/ui/web/cf_access.py
"""Cloudflare Access identity for the web layer.

Two modes, chosen purely by environment:

* **Local mode** (no ``CF_ACCESS_TEAM_DOMAIN`` / ``CF_ACCESS_AUD``): the app runs
  exactly as before — no per-user data, no login. This is the DNA "no registration"
  path for running uvicorn on your own machine.
* **Access mode** (both env vars set): every request must carry a valid
  ``Cf-Access-Jwt-Assertion`` that Cloudflare Access injects. The JWT is verified
  (RS256 signature via the team's JWKS, plus ``aud``/``iss``/``exp``) and its
  ``email`` claim becomes the per-user key. Requests without a valid identity are
  refused — the app never trusts an unverified header.

Get the two values from the Cloudflare Zero Trust dashboard:
  CF_ACCESS_TEAM_DOMAIN  -> your team domain, e.g. ``myteam.cloudflareaccess.com``
  CF_ACCESS_AUD          -> Access app → Overview → "Application Audience (AUD) Tag"
"""
from __future__ import annotations

import os
from typing import Optional


def team_domain() -> Optional[str]:
    d = (os.environ.get("CF_ACCESS_TEAM_DOMAIN") or "").strip()
    if not d:
        return None
    d = d.replace("https://", "").replace("http://", "").strip("/")
    return d or None


def aud() -> Optional[str]:
    a = (os.environ.get("CF_ACCESS_AUD") or "").strip()
    return a or None


def access_enabled() -> bool:
    """True when both config values are present → per-user Access mode."""
    return bool(team_domain() and aud())


def issuer() -> str:
    return f"https://{team_domain()}"


def certs_url() -> str:
    return f"https://{team_domain()}/cdn-cgi/access/certs"


def verify_access_token(token: str, *, signing_key, audience: str, issuer: str) -> dict:
    """Pure JWT verification (RS256 + aud + iss + exp). Returns claims or raises.

    Kept dependency-injectable (signing_key/audience/issuer as args) so it can be
    unit-tested with a self-signed key, without contacting Cloudflare.
    """
    import jwt

    return jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
    )


_jwk_client = None  # cached across requests (JWKS keys are fetched once)


def _client():
    global _jwk_client
    if _jwk_client is None:
        import jwt

        _jwk_client = jwt.PyJWKClient(certs_url())
    return _jwk_client


def email_from_token(token: Optional[str]) -> Optional[str]:
    """Verify a ``Cf-Access-Jwt-Assertion`` and return the identity email, or None."""
    if not token:
        return None
    try:
        signing_key = _client().get_signing_key_from_jwt(token).key
        claims = verify_access_token(
            token, signing_key=signing_key, audience=aud(), issuer=issuer()
        )
        return claims.get("email") or claims.get("identity") or claims.get("sub")
    except Exception:
        return None

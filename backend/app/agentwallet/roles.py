"""Role checks for the API (plan section 3.3: every route requires a session and a role).

Amanah's session layer is not in this repository, so the standalone build reads the caller's role from
the X-Amanah-Role header and the user from X-Amanah-User, as agreed with lane D. When the routes move
into Amanah, replace `current_identity` with Amanah's session dependency; `require` stays as it is.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

FINANCE_OFFICER = "finance_officer"
TRUSTEE = "trustee"
GUARDIAN = "guardian"
EXTERNAL_AUDITOR = "external_auditor"
ROLES = (FINANCE_OFFICER, TRUSTEE, GUARDIAN, EXTERNAL_AUDITOR)


@dataclass(frozen=True)
class Identity:
    role: str
    user: str


def current_identity(x_amanah_role: str | None = Header(default=None),
                     x_amanah_user: str | None = Header(default=None)) -> Identity:
    if x_amanah_role not in ROLES:
        raise HTTPException(status_code=401, detail=f"Send X-Amanah-Role, one of: {', '.join(ROLES)}.")
    return Identity(role=x_amanah_role, user=x_amanah_user or "unnamed")


def require(*roles: str):
    """A dependency that admits only the given roles; with no roles, any signed-in role."""

    def dependency(identity: Identity = Depends(current_identity)) -> Identity:
        if roles and identity.role not in roles:
            raise HTTPException(status_code=403, detail=f"This route is for the {' or '.join(roles)} role.")
        return identity

    return dependency

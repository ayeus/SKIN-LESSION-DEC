# Local accounts, roles and data ownership

This adds local research access controls. It is not a claim of HIPAA compliance, clinical production approval, SSO, MFA, encrypted storage or security certification. Only authorized, appropriately de-identified data is permitted.

## Bootstrap and actual owner action

Existing DERMA_API_TOKEN remains an environment-managed administrator token. No default password or account is seeded. Existing public datasets and runs have no named owner after migration and are visible only to administrators until an explicit read grant is created.

1. Back up the database/storage and run `.venv/bin/python -m alembic -c backend/alembic.ini upgrade head` (revision 002). The development SQLite DB was backed up locally before migration; four imported datasets and three real runs were preserved, zero users seeded.
2. Connect with the environment owner token. In Data & model status → Accounts and data access, create named accounts. The human owner chooses the username/password/role; do not send credentials through chat or commit them.
3. Named users sign in using the local account form. Tokens live in browser memory, not localStorage. No public registration exists.
4. If removing bootstrap access, first verify a named administrator sign-in, then unset DERMA_API_TOKEN and restart the server. Rotating/unsetting the environment value revokes bootstrap access. Browser lock cannot revoke an environment token.

## Roles and visibility

| Capability | Administrator | Researcher | Viewer |
|---|---|---|---|
| Dataset registry/rows/source schema | All datasets | Owned or explicitly read-granted | Explicitly read-granted |
| Imports/image processing/analyses/score retention | Allowed | Allowed on accessible input; new resources owned by user | Denied |
| Raw clinical source and images for canonical CNN training | Administrator-controlled configured paths | Denied | Denied |
| Start canonical training / select global research model | Allowed | Denied | Denied |
| Analysis history/results/export | All | Own runs, with current access to their input datasets | Own runs if any, with current input access |
| Share a dataset read grant | Any dataset | Own datasets only | Denied |
| Create/enable/disable accounts | Allowed | Denied | Denied |
| Use administrator-selected research model ephemerally | Allowed | Allowed | Allowed |

A grant permits reading the selected dataset; it never shares other users' analysis reports. Researchers can generate private reports from granted inputs. Revoking a source grant also blocks access to their derived reports/exports, including relationship reports' parent inputs. Revocation does not delete previously downloaded copies or abort an already running computation. No automatic clinical or identity linkage is performed.

Permission checks apply to metadata, dashboards/counts, table filtering, analysis submission, reports and artifact export—not only navigation. Hidden records return 404. Viewer mutations return 403. The UI states its read-only role; the backend enforces permissions independently. Canonical selected models are an administrator-published research artifact, separate from private raw training sources.

## Passwords and sessions

- Passwords: per-user 16-byte random salt; PBKDF2-HMAC-SHA256, 600,000 iterations; only salted hashes stored. New passwords require 12–1024 characters. This uses the Python standard library and does not assert a FIPS-validated runtime. Password hash work factor follows the [OWASP password storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- Session tokens: 32 random bytes encoded URL-safe; only SHA-256 digests stored (fast hashing is used for high-entropy session tokens, not passwords).
- Absolute lifetime defaults to eight hours; DERMA_SESSION_HOURS supports 1–168 hours. No automatic refresh. Every request checks session expiry/revocation and active account status.
- Logout revokes a named session. Disabling an account revokes all its sessions and prevents sign-in. Browser 401 handling clears cached registry/results and requests sign-in again. If revocation cannot be confirmed over the network, local access is cleared with an explicit notice.
- Failed login handling: generic errors, expensive dummy-hash verification for unknown users, five failures per username/client within 15 minutes trigger a 15-minute cooldown. This is a local best-effort throttle, not distributed/high-traffic protection. Put rate limits and a trusted TLS proxy in front of any shared deployment; do not trust arbitrary forwarded headers.
- Auth validation responses omit submitted input values, including passwords. API/audit outputs exclude password hashes and raw session tokens. Audit events record actor IDs, actions and resource IDs, never note bodies or passwords. Administrators can inspect the bounded `/audit` endpoint and the Settings audit view; non-admin users cannot access it.

## Storage and limits

New storage roots use mode 0700; the existing development data directory was restricted to owner access. Restrict deployment storage and `.env` permissions explicitly (e.g. owner-only data directory and chmod 600 .env). Filesystem access remains an OS responsibility; these API controls do not encrypt files. No password-reset/email flow, MFA, SSO, idle timeout, Argon2 migration, institutional retention service, distributed throttling or independent penetration test is claimed.

Schema: users, access_sessions, login_throttles; owner_id on datasets/runs; dataset_grants; actor_id on audit_events. Optional external PostgreSQL is covered by migration/integration checks. Tests use isolated synthetic users/passwords and disposable storage, never real accounts.

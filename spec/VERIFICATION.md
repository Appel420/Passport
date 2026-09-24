# Passport Verification Spec v0.1.0

How any app verifies a Passport token.

## Verification order (fail-closed)

1. **Parse** — decode the token as JSON. Reject malformed input.
2. **Version check** — `passport_version` must be a supported schema version.
3. **Required fields** — all fields in `token.schema.json` must be present.
4. **Timestamp check** — `issued_at` must be in the past; `expires_at` (if set) must be in the future.
5. **Nonce check** — reject reused nonces (replay protection).
6. **Signature verification** — verify `signature.value` against the canonical payload using `signature.public_key` and `signature.algorithm`.
7. **Owner binding** — the verified owner must match the expected builder for the requested action.
8. **Build binding** — if the token is used to claim a specific build, that build must appear in `builds` with matching evidence.

If any step fails: no authority, no attribution credit, no access. The token is advisory until verified; verification is the gate.

## What verification grants

- **Recognition** — the app knows who the builder is without a fresh login
- **Attribution** — the builder's record attaches to any output they produce
- **Continuity** — session state, build history, and preferences can be restored from the token

## What verification does not grant

- Administrative access
- Ability to mutate protected state (that requires RFC-002 proofs)
- Trust in unverified claims about external work

## Cross-app flow

1. Builder signs in to App A. App A issues or retrieves a Passport token.
2. Builder opens App B. App B reads the token (local storage, QR, or URL).
3. App B runs the verification order above.
4. If valid: App B recognizes the builder and restores their record.
5. If invalid: App B treats the builder as unrecognized.

## Security notes

- Tokens should be stored encrypted at rest on the device.
- Private keys never leave the device.
- Apps verify locally where possible; a central endpoint is optional.
- Revocation: a builder can invalidate all tokens by rotating their keypair.

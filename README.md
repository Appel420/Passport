# Passport

**Portable builder identity and provenance layer for the Sovereignty One / GateOne stack.**

Your passport is a signed, portable record of who you are, what you built, and when you built it. It travels with you across apps and sessions instead of dying at each login. Every app that recognizes Passport sees the same builder: your account, your builds, your contributions, your timestamps.

## Core principles

- **Identity is portable** — one signed token, recognized everywhere
- **Attribution by default** — every build carries its creator's record
- **Evidence before assertion** — provenance claims backed by dated, verifiable artifacts
- **Opt-in registry** — builders control what gets published
- **Fail-closed** — unrecognized or unverified tokens get no authority

## Structure

```
Passport/
├── README.md              # this file
├── schema/
│   └── token.schema.json  # signed identity token format
├── spec/
│   └── VERIFICATION.md    # how any app verifies a Passport token
├── registry/
│   └── REGISTRY.md       # opt-in builder registry format
└── examples/
    └── sample-token.json  # example signed token
```

## Status

- [x] Repo created under Appel420 (sovereign owner)
- [x] Token schema defined (v0.1.0)
- [x] Verification spec drafted
- [x] Registry format drafted
- [ ] Signing implementation (Ed25519)
- [ ] Verification endpoint
- [ ] Cross-app integration

## Attribution

Created by Appel420 / Sovereignty One, 2026-09-24T22:30Z.
Architecture derived from Sovereignty-AI-Gate (RFC-002 Proof-Gated Authority, Owner-Bound Continuity v1) and GitSovereign.

## References

- Sovereignty-AI-Gate: https://github.com/Appel420/Sovereignty-AI-Gate
- GitSovereign: https://github.com/Appel420/GitSovereign
- Sovereignty-Grok-Discord: https://github.com/Appel420/Sovereignty-Grok-Discord

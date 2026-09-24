# Branch policy

**Invariant:** No repository operation may assume `main`, `master`, `base`, `develop`, or any other fixed branch name. Branch selection must be resolved per repository and recorded in the operation evidence.

## Resolution contract (fail closed)

```
Explicit BASE_BRANCH / PASSPORT_BRANCH / GIT_BRANCH
       ↓
Branch exists on remote?
       ↓
YES → use it
NO  → resolve repository default_branch (GET /repos/{owner}/{repo})
       ↓
Default exists on remote?
       ↓
YES → use it
NO  → FAIL CLOSED (DENY)
```

There is **no** silent fallback to `main`, `base`, or “first listed branch.” Branch list order is not an authority decision.

## Fetch pattern

```bash
BRANCH="$(python3 scripts/resolve_branch.py Appel420 Passport)" || exit 1
curl -fsSL \
  "https://raw.githubusercontent.com/Appel420/Passport/${BRANCH}/verify.py"
```

Wrong (hardcoded assumption):

```text
https://raw.githubusercontent.com/Appel420/Passport/main/
```

## Explicit working branch for this repo

If `base` is the intended integration line for Passport, set it **explicitly**:

```bash
export BASE_BRANCH=base
# or
export PASSPORT_BRANCH=base
```

Do not bake that preference into shared resolvers as a universal rule.

Changing GitHub’s repository `default_branch` is a **separate administration operation**. It is not required for safe resolution when `BASE_BRANCH` is set and verified.

## Evidence

Every resolve operation should record:

- owner / repo
- source of selection (`env:BASE_BRANCH` | `api:default_branch`)
- resolved branch name
- whether existence was verified
- outcome: `ALLOW` | `DENY`

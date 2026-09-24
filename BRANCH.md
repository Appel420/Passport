# Branch policy

**Do not hardcode `main`.**

## Integration branch

- Working / integration branch: **`base`**
- `main` may exist as a historical default from repo creation; it is not the assumed target.
- All new commits for Passport go to **`base`** unless a feature branch is named explicitly.

## Resolve the branch (scripts / CI / agents)

Never assume:

```text
https://raw.githubusercontent.com/OWNER/REPO/main/...
```

Resolve in this order:

1. Explicit env override: `PASSPORT_BRANCH` or `GIT_BRANCH`
2. If branch **`base`** exists on the remote → use `base`
3. Else GitHub API `default_branch` from `GET /repos/{owner}/{repo}`
4. Else first available branch from `GET /repos/{owner}/{repo}/branches`

Raw URL form:

```text
https://raw.githubusercontent.com/{owner}/{repo}/{resolved_branch}/{path}
```

Git refs:

```text
refs/heads/{resolved_branch}
```

## Setting GitHub default

To make GitHub treat `base` as the repository default (PRs, clone HEAD, Actions defaults):

1. Open https://github.com/Appel420/Passport/settings
2. Branches → Default branch → switch to **`base`**

API equivalent (requires admin token):

```bash
gh api repos/Appel420/Passport -X PATCH -f default_branch=base
```

Until that is set, API `default_branch` may still report `main`. Scripts must still prefer `base` when present.

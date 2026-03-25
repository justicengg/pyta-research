# Branch Conflict Playbook

## Why this happened

This branch showed `This branch has conflicts that must be resolved` because:

1. The PR base branch was `main`.
2. `origin/main` had moved forward while the feature branch had not absorbed those new commits.
3. Both branches touched the same files, especially:
   - `frontend/src/components/layout/CanvasStage.tsx`
   - `src/api/routers/sources.py`

In this repo, conflicts are especially likely when:
- frontend interaction work and source-ingestion work both move in parallel
- one branch follows the new PYTA product direction while another branch adds old-panel or side-panel flows
- worktrees exist, but the current branch is not refreshed from its base before a push/PR update

## Rules to avoid this next time

### 1. Always confirm the real base branch before pushing
Before opening or updating a PR, confirm:

- Which branch this work should merge into
- Whether the PR base should be `main` or another active product branch

Do not assume.

### 2. Refresh from base before the final push
Before the final push for a UI or product branch:

1. `git fetch origin`
2. Check ahead/behind against the intended base branch
3. If behind, merge or rebase before pushing

Recommended quick checks:

```bash
git branch --show-current
git fetch origin
git rev-list --left-right --count HEAD...origin/main
```

If the second number is not `0`, your branch is behind `main`.

### 3. Resolve conflicts locally, not on GitHub
Do not rely on the GitHub conflict editor for this project.

Reason:
- frontend and product-direction conflicts here are semantic, not just textual
- the correct resolution often depends on current PYTA product decisions

Always resolve in the local worktree, then rebuild.

### 4. Protect the current product direction
When merging:

- do not blindly restore removed patterns like the right observation panel
- keep the current source of truth for product direction in mind
- preserve newer UX decisions even when `main` reintroduces older interaction structures

### 5. After conflict resolution, always validate build
Minimum required:

```bash
cd frontend
npm run build
```

If the conflict touches backend routes or schemas, also run the relevant API/test checks.

## Recommended push workflow

### For feature work
```bash
git branch --show-current
git fetch origin
git rev-list --left-right --count HEAD...origin/main
git status --short
```

If behind:
```bash
git merge origin/main
```

Then:
```bash
cd frontend && npm run build
git add ...
git commit -m "..."
git push
```

## Worktree-specific guidance

This repo uses worktrees. That is helpful, but it does **not** prevent branch conflicts by itself.

Worktrees solve:
- local context isolation
- cleaner development surfaces
- fewer stash/switch problems

Worktrees do **not** solve:
- branch divergence from `main`
- wrong PR base selection
- semantic conflicts between product directions

So even inside a clean worktree, you still need to:
- fetch
- compare with base
- merge/rebase before final push

## Practical checklist before final push

- [ ] Confirm current branch name
- [ ] Confirm target PR base branch
- [ ] `git fetch origin`
- [ ] Check ahead/behind vs base
- [ ] Merge/rebase if behind
- [ ] Run build locally
- [ ] Re-check `git status`
- [ ] Push only after the branch is conflict-clean

## Practical checklist when conflicts already happened

1. Identify the actual conflicting files
2. Separate:
   - text conflict
   - product-direction conflict
3. Resolve according to current product truth, not whichever side is newer
4. `git add` resolved files
5. Rebuild
6. Commit the merge resolution
7. Push again

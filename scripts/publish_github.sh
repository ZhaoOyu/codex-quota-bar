#!/usr/bin/env bash
# Run in the user's authenticated terminal. Never exports or prints tokens.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  printf '%s\n' 'Usage: bash scripts/publish_github.sh' \
    'Publishes the current source to ZhaoOyu/codex-quota-bar (public),' \
    'then waits for the version-tag build and GitHub Release.' \
    'Requires gh authenticated as ZhaoOyu, git, python3, tar, and network access.'
  exit 0
fi
if [[ $# -ne 0 ]]; then
  printf '%s\n' 'Unknown argument. Use --help.' >&2
  exit 2
fi

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
repo='ZhaoOyu/codex-quota-bar'
for tool in gh git python3 tar; do
  command -v "$tool" >/dev/null || { printf 'Missing dependency: %s\n' "$tool" >&2; exit 1; }
done
cd "$project_dir"
python3 -m unittest discover -s tests -v
version="$(python3 -c 'from codex_quota_bar import __version__; print("v" + __version__)')"
account="$(gh api user --jq .login)"
if [[ "$account" != 'ZhaoOyu' ]]; then
  printf 'Expected ZhaoOyu, but gh is logged in as %s. No repository changed.\n' "$account" >&2
  exit 1
fi

# OAuth login without --scopes workflow cannot push a GitHub Actions file.
# Fine-grained tokens do not expose this header; their server-side permissions apply.
scopes="$(gh api --include user | awk 'tolower($0) ~ /^x-oauth-scopes:/ {sub(/^[^:]*:[ ]*/, ""); gsub(/\r/, ""); print}')"
if [[ -n "$scopes" && ",${scopes// /}," != *',workflow,'* ]]; then
  printf '%s\n' 'GitHub requires the workflow scope to upload the build configuration.'
  gh auth refresh --hostname github.com --scopes workflow
fi

# The source workspace may have a protected .git. Use an isolated checkout,
# and copy only release source files, never user config, logs, or credentials.
publish_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-quota-publish.XXXXXX")"
printf 'Publication checkout (retained for inspection): %s\n' "$publish_dir"
repo_names="$(gh repo list ZhaoOyu --limit 1000 --json nameWithOwner --jq '.[].nameWithOwner')"
if ! printf '%s\n' "$repo_names" | grep -Fqx "$repo"; then
  gh repo create "$repo" --public \
    --description 'Native macOS and Ubuntu status bar for Codex five-hour and weekly remaining quotas'
fi
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' \
  clone "https://github.com/$repo.git" "$publish_dir/repo"
checkout="$publish_dir/repo"
if git -C "$checkout" rev-parse --verify HEAD >/dev/null 2>&1; then
  if [[ ! -f "$checkout/pyproject.toml" ]] || \
     ! grep -Fqx 'name = "codex-quota-bar"' "$checkout/pyproject.toml"; then
    printf '%s\n' 'Existing repository contains a different project; stopped without overwriting it.' >&2
    exit 1
  fi
  git -C "$checkout" checkout main
else
  git -C "$checkout" checkout -b main
fi

source_paths=(.gitignore .github pyproject.toml README.md LICENSE VALIDATION.md \
              launcher.py codex_quota_bar packaging scripts tests)
tar --exclude='__pycache__' --exclude='*.pyc' -cf - "${source_paths[@]}" | tar -xf - -C "$checkout"
cd "$checkout"
git config credential.helper ''
git config --add credential.helper '!gh auth git-credential'
account_id="$(gh api user --jq .id)"
git config user.name 'ZhaoOyu'
git config user.email "${account_id}+ZhaoOyu@users.noreply.github.com"
git add -- "${source_paths[@]}"
if ! git diff --cached --quiet; then
  git commit -m "Release Codex Quota Bar $version"
fi
commit="$(git rev-parse HEAD)"
if git rev-parse --verify "refs/tags/$version" >/dev/null 2>&1; then
  if [[ "$(git rev-list -n 1 "$version")" != "$commit" ]]; then
    printf 'Tag %s already points to different code. Bump the app version; no tag was overwritten.\n' "$version" >&2
    exit 1
  fi
else
  git tag "$version"
fi
# Separate the initial branch publication from the tag event, so the workflow
# is already present on the default branch when the release tag is pushed.
git push origin main
git push origin "refs/tags/$version"
printf 'Source published: https://github.com/%s\n' "$repo"

if gh release view "$version" --repo "$repo" --json url --jq .url 2>/dev/null; then
  exit 0
fi
printf '%s\n' 'Waiting for GitHub to schedule the release build…'
run_id=''
for attempt in {1..30}; do
  run_id="$(gh run list --repo "$repo" --workflow build.yml --branch "$version" \
    --commit "$commit" --event push --limit 1 --json databaseId --jq '.[0].databaseId // empty')"
  [[ -n "$run_id" ]] && break
  sleep 4
done
if [[ -z "$run_id" ]]; then
  # Existing tags do not emit another push event. Recover without moving or
  # deleting an immutable release tag. Dispatching on the tag keeps github.ref
  # under refs/tags/, which enables the workflow's release job.
  printf 'No tag-push build found; dispatching the workflow on %s…\n' "$version"
  gh workflow run build.yml --repo "$repo" --ref "$version"
  for attempt in {1..30}; do
    run_id="$(gh run list --repo "$repo" --workflow build.yml --branch "$version" \
      --commit "$commit" --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId // empty')"
    [[ -n "$run_id" ]] && break
    sleep 4
  done
  if [[ -z "$run_id" ]]; then
    printf 'Workflow dispatched, but its run is not visible yet. Check https://github.com/%s/actions\n' "$repo" >&2
    exit 1
  fi
fi
if ! gh run watch "$run_id" --repo "$repo" --exit-status; then
  printf 'Build failed. Share this URL for diagnosis: https://github.com/%s/actions/runs/%s\n' "$repo" "$run_id" >&2
  exit 1
fi
gh release view "$version" --repo "$repo" --json url --jq .url

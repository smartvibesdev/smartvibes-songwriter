#!/usr/bin/env bash
# Build the frontend and deploy the whole stack to AWS.
#
# Usage:
#   scripts/deploy.sh         build the frontend, then `cdk deploy` (asks before IAM changes)
#   scripts/deploy.sh diff    build the frontend, then `cdk diff` only (changes nothing)
#
# Run from anywhere; paths are resolved from this file's location.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AWS_PROFILE="${AWS_PROFILE:-smartvibes-dev}"
MODE="${1:-deploy}"

if [[ "$MODE" != "deploy" && "$MODE" != "diff" ]]; then
  echo "Usage: $0 [deploy|diff]" >&2
  exit 1
fi

echo "==> AWS profile: $AWS_PROFILE"
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "==> Not logged in (or session expired). Logging in..."
  aws sso login --profile "$AWS_PROFILE"
fi

if [[ ! -f "$ROOT/frontend/.env.local" ]]; then
  echo "Missing frontend/.env.local (see docs/deployment.md)." >&2
  exit 1
fi

echo "==> Building frontend"
(cd "$ROOT/frontend" && npm run build)

echo "==> cdk $MODE"
cd "$ROOT/infra"
# shellcheck disable=SC1091
source .venv/bin/activate
# Only the app stack; the GitHub access stack (SmartvibesSongwriter-github) is separate.
cdk "$MODE" SmartvibesSongwriter-dev

if [[ "$MODE" == "deploy" ]]; then
  echo "==> Done. Outputs are listed above (SiteUrl, ApiUrl, ...)."
fi

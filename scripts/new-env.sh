#!/usr/bin/env bash
# First deploy of a NEW environment (dev, test or prod), by hand.
#
# Why by hand: the GitHub Deploy workflow needs variables (API URL, Cognito IDs)
# that only exist after the stack has been deployed once. After this script, add
# those variables to the GitHub environment and use the workflow from then on.
#
# Usage: scripts/new-env.sh prod
set -euo pipefail

ENV_NAME="${1:-}"
if [[ "$ENV_NAME" != "dev" && "$ENV_NAME" != "test" && "$ENV_NAME" != "prod" ]]; then
  echo "Usage: $0 <dev|test|prod>" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK="SmartvibesSongwriter-$ENV_NAME"
export AWS_PROFILE="${AWS_PROFILE:-smartvibes-dev}"

cd "$ROOT"
if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "Switch to main first (git checkout main). This deploys what is on main." >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "You have uncommitted changes. Commit or stash them first." >&2
  exit 1
fi
git pull --ff-only

echo "==> AWS profile: $AWS_PROFILE"
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "==> Not logged in (or session expired). Logging in..."
  aws sso login --profile "$AWS_PROFILE"
fi

# A leftover build would upload another environment's values to this site.
echo "==> Removing any local frontend build"
rm -rf "$ROOT/frontend/dist"

cd "$ROOT/infra"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> cdk diff $STACK (everything should be new; nothing in other environments)"
cdk diff "$STACK" -c env="$ENV_NAME" || true

read -r -p "Deploy $STACK now? [y/N] " ANSWER
if [[ "$ANSWER" != "y" && "$ANSWER" != "Y" ]]; then
  echo "Cancelled. Nothing was deployed."
  exit 0
fi

cdk deploy "$STACK" -c env="$ENV_NAME"

echo
echo "==> Add these as variables on the GitHub environment '$ENV_NAME'"
echo "    (repo Settings > Environments > $ENV_NAME > Environment variables):"
OUT() {
  aws cloudformation describe-stacks --stack-name "$STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
echo "    VITE_API_URL              = $(OUT ApiUrl)"
echo "    VITE_COGNITO_USER_POOL_ID = $(OUT UserPoolId)"
echo "    VITE_COGNITO_CLIENT_ID    = $(OUT UserPoolClientId)"
echo "    VITE_COGNITO_REGION       = us-east-1"
echo "    AWS_DEPLOY_ROLE_ARN       = (same value as the dev environment)"
echo
echo "Then: GitHub > Actions > Deploy > Run workflow > choose '$ENV_NAME' > approve."

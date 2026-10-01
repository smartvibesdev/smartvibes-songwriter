import os

import aws_cdk as cdk

from stacks.github_deploy_stack import GithubDeployStack
from stacks.songwriter_stack import SongwriterStack

app = cdk.App()
aws_env = cdk.Environment(
    # Account and region come from the active AWS CLI profile or credentials
    # (CDK_DEFAULT_ACCOUNT / CDK_DEFAULT_REGION). Nothing is committed.
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

# Stage name drives resource naming: smartvibes-songwriter-<env>-<resource>.
# Override with: cdk synth -c env=prod
env_name = app.node.try_get_context("env") or "dev"

SongwriterStack(
    app,
    f"SmartvibesSongwriter-{env_name}",
    env_name=env_name,
    env=aws_env,
)

# Account-level setup that lets GitHub Actions deploy into one AWS account.
# Each environment lives in its own account, so the role in that account trusts
# only that environment's GitHub workflows. Deployed once per account, by hand:
#   cdk deploy SmartvibesSongwriter-github -c env=dev  --profile smartvibes-dev
#   cdk deploy SmartvibesSongwriter-github -c env=prod --profile smartvibes-prod
GithubDeployStack(
    app,
    "SmartvibesSongwriter-github",
    # The repo's name as it appears in GitHub's OIDC tokens (contains permanent IDs).
    github_subject_prefix="repo:smartvibesdev@165607164/smartvibes-songwriter@1395969992",
    github_environments=[env_name],
    env=aws_env,
)

app.synth()

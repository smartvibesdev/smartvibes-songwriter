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

# Account-level setup that lets GitHub Actions deploy. Deployed separately, by hand:
#   cdk deploy SmartvibesSongwriter-github
GithubDeployStack(
    app,
    "SmartvibesSongwriter-github",
    github_repo="smartvibesdev/smartvibes-songwriter",
    github_environments=["dev", "test", "prod"],
    env=aws_env,
)

app.synth()

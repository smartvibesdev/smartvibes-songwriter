import os

import aws_cdk as cdk

from stacks.songwriter_stack import SongwriterStack

app = cdk.App()

# Stage name drives resource naming: smartvibes-songwriter-<env>-<resource>.
# Override with: cdk synth -c env=prod
env_name = app.node.try_get_context("env") or "dev"

SongwriterStack(
    app,
    f"SmartvibesSongwriter-{env_name}",
    env_name=env_name,
    # Account and region come from the active AWS CLI profile
    # (CDK_DEFAULT_ACCOUNT / CDK_DEFAULT_REGION). Nothing is committed.
    # Region is intended to be us-east-1: set AWS_REGION / profile accordingly.
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION"),
    ),
)

app.synth()

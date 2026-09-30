import aws_cdk as cdk
from aws_cdk import aws_iam as iam
from constructs import Construct

GITHUB_OIDC_URL = "https://token.actions.githubusercontent.com"
# Qualifier of the default `cdk bootstrap` (see the CDKToolkit stack).
BOOTSTRAP_QUALIFIER = "hnb659fds"


class GithubDeployStack(cdk.Stack):
    """Lets one GitHub Actions workflow deploy the app, with no stored AWS keys.

    GitHub proves its identity to AWS with a short-lived OIDC token. The role
    below can be assumed only by workflows of `github_repo` that run in the
    given GitHub *environment*, so a required-reviewer rule on that environment
    acts as the approval gate.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        github_repo: str,  # "owner/repo"
        github_environment: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Only one provider per URL can exist in an AWS account.
        provider = iam.OpenIdConnectProvider(
            self,
            "GithubOidcProvider",
            url=GITHUB_OIDC_URL,
            client_ids=["sts.amazonaws.com"],
        )

        role = iam.Role(
            self,
            "DeployRole",
            role_name="smartvibes-songwriter-github-deploy",
            description="Assumed by GitHub Actions to run cdk deploy",
            max_session_duration=cdk.Duration.hours(1),
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{github_repo}:environment:{github_environment}"
                        ),
                    }
                },
            ),
        )

        # `cdk deploy` does its work through the roles created by `cdk bootstrap`;
        # this role only needs to assume them and read the bootstrap version.
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[
                    f"arn:{self.partition}:iam::{self.account}:role/"
                    f"cdk-{BOOTSTRAP_QUALIFIER}-*-role-{self.account}-{self.region}"
                ],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:{self.partition}:ssm:{self.region}:{self.account}:"
                    f"parameter/cdk-bootstrap/{BOOTSTRAP_QUALIFIER}/version"
                ],
            )
        )

        cdk.CfnOutput(self, "DeployRoleArn", value=role.role_arn)

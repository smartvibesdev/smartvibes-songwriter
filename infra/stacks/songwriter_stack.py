import subprocess
import sys
from pathlib import Path

import aws_cdk as cdk
import jsii
from aws_cdk import (
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_authorizers as apigw_auth,
    aws_apigatewayv2_integrations as apigw_int,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@jsii.implements(cdk.ILocalBundling)
class LocalPipBundling:
    """Bundle the backend without Docker: pip-install Lambda-compatible wheels."""

    def try_bundle(self, output_dir: str, *, image=None, **kwargs) -> bool:
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "install",
                    "-r", str(BACKEND_DIR / "requirements.txt"),
                    "--target", output_dir,
                    "--platform", "manylinux2014_aarch64",
                    "--implementation", "cp",
                    "--python-version", "3.12",
                    "--only-binary=:all:",
                    "--upgrade",
                    "--quiet",
                ],
                check=True,
            )
            subprocess.run(
                ["cp", "-r", str(BACKEND_DIR / "app"), output_dir], check=True
            )
        except subprocess.CalledProcessError:
            return False
        return True


class SongwriterStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env_name: str,
        google_client_id: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        prefix = f"smartvibes-songwriter-{env_name}"
        retain = cdk.RemovalPolicy.RETAIN

        # --- DynamoDB: single table (plan section 5) ---
        table = dynamodb.Table(
            self,
            "Table",
            table_name=f"{prefix}-table",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=retain,
        )

        # --- Cognito user pool ---
        # Email/password sign-in works directly; Google sign-in goes through
        # Cognito's hosted domain (defined below, once the site URL exists).
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{prefix}-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=retain,
        )
        # --- Static front end: private S3 bucket behind CloudFront (OAC) ---
        site_bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # build artifacts only
            auto_delete_objects=True,
        )
        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment=f"{prefix}-web",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            # SPA fallback
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403, response_http_status=200, response_page_path="/index.html"
                ),
                cloudfront.ErrorResponse(
                    http_status=404, response_http_status=200, response_page_path="/index.html"
                ),
            ],
        )
        # Upload the built front end (run `npm run build` in frontend/ first).
        # Skipped when there is no build, so `cdk synth` in CI still works.
        if FRONTEND_DIST.is_dir():
            s3deploy.BucketDeployment(
                self,
                "SiteDeployment",
                sources=[s3deploy.Source.asset(str(FRONTEND_DIST))],
                destination_bucket=site_bucket,
                distribution=distribution,
                distribution_paths=["/*"],
            )

        # --- Cognito: Google sign-in, hosted domain and web client ---
        # The Google client secret is NOT in the code. It is read at deploy time
        # from AWS Secrets Manager (create it once per account, see
        # docs/deployment.md). The client ID is public.
        google_idp = cognito.UserPoolIdentityProviderGoogle(
            self,
            "GoogleIdp",
            user_pool=user_pool,
            client_id=google_client_id,
            client_secret_value=cdk.SecretValue.secrets_manager(
                "smartvibes-songwriter/google-oauth-client-secret"
            ),
            scopes=["openid", "email", "profile"],
            attribute_mapping=cognito.AttributeMapping(
                email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                fullname=cognito.ProviderAttribute.GOOGLE_NAME,
            ),
        )
        # Hosted sign-in domain. The Google client must list
        # https://<prefix>.auth.<region>.amazoncognito.com/oauth2/idpresponse as an
        # authorized redirect URI. The prefix must be unique across AWS.
        # Managed login (not the classic hosted UI), because only it forwards the
        # `prompt` parameter to Google, which the web app uses to show Google's
        # account chooser after a sign-out (ADR 0009).
        user_pool_domain = user_pool.add_domain(
            "HostedDomain",
            cognito_domain=cognito.CognitoDomainOptions(domain_prefix=prefix),
            managed_login_version=cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
        )
        site_url = f"https://{distribution.distribution_domain_name}/"
        user_pool_client = user_pool.add_client(
            "WebClient",
            user_pool_client_name=f"{prefix}-web",
            generate_secret=False,  # public SPA client
            auth_flows=cognito.AuthFlow(user_srp=True),
            prevent_user_existence_errors=True,
            # Cognito's default is 30 days. A stolen refresh token stays useful for
            # this long, so keep it short (ADR 0008).
            refresh_token_validity=cdk.Duration.days(7),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
                cognito.UserPoolClientIdentityProvider.GOOGLE,
            ],
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=[site_url, "http://localhost:5173/"],
                logout_urls=[site_url, "http://localhost:5173/"],
            ),
        )
        user_pool_client.node.add_dependency(google_idp)

        # Managed login needs a branding style for each app client created through
        # the API. Cognito's default values are enough: users are sent straight to
        # Google and rarely see Cognito's own pages.
        cognito.CfnManagedLoginBranding(
            self,
            "WebClientBranding",
            user_pool_id=user_pool.user_pool_id,
            client_id=user_pool_client.user_pool_client_id,
            use_cognito_provided_values=True,
        )

        # --- Lambda: FastAPI via Mangum ---
        api_fn = _lambda.Function(
            self,
            "ApiFunction",
            function_name=f"{prefix}-api",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.ARM_64,
            handler="app.main.handler",
            code=_lambda.Code.from_asset(
                str(BACKEND_DIR),
                bundling=cdk.BundlingOptions(
                    # Docker fallback if the local bundler fails.
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    platform="linux/arm64",
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r app /asset-output/",
                    ],
                    local=LocalPipBundling(),
                ),
            ),
            memory_size=512,
            timeout=cdk.Duration.seconds(30),
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(api_fn)

        # --- API Gateway HTTP API with Cognito JWT authorizer ---
        allowed_origins = [f"https://{distribution.distribution_domain_name}", "http://localhost:5173"]
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name=f"{prefix}-api",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=allowed_origins,
                allow_methods=[apigwv2.CorsHttpMethod.ANY],
                allow_headers=["authorization", "content-type"],
            ),
        )
        # No $default route: a catch-all route would also match browser CORS
        # preflight (OPTIONS) requests and demand a token, which browsers can't
        # send. With none, API Gateway answers preflights itself from the CORS
        # settings above.
        # /health is public; every other path requires a valid Cognito JWT.
        lambda_integration = apigw_int.HttpLambdaIntegration("ApiIntegration", api_fn)
        http_api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=lambda_integration,
            authorizer=apigwv2.HttpNoneAuthorizer(),
        )
        http_api.add_routes(
            path="/{proxy+}",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.POST,
                apigwv2.HttpMethod.PUT,
                apigwv2.HttpMethod.PATCH,
                apigwv2.HttpMethod.DELETE,
            ],
            integration=lambda_integration,
            authorizer=apigw_auth.HttpUserPoolAuthorizer(
                "CognitoAuthorizer", user_pool, user_pool_clients=[user_pool_client]
            ),
        )
        # Request-flood protection (plan section 6). Tune later.
        default_stage = http_api.default_stage.node.default_child
        default_stage.default_route_settings = apigwv2.CfnStage.RouteSettingsProperty(
            throttling_burst_limit=20, throttling_rate_limit=10
        )

        # --- Outputs ---
        cdk.CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        cdk.CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        cdk.CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        cdk.CfnOutput(
            self,
            "CognitoDomain",
            value=f"{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
        )
        cdk.CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        cdk.CfnOutput(self, "TableName", value=table.table_name)

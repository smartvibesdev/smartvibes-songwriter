# Infrastructure (AWS CDK, Python)

Region: `us-east-1`. Account/region are read from your AWS CLI profile
(`CDK_DEFAULT_ACCOUNT`, `CDK_DEFAULT_REGION`); nothing is hardcoded.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CDK_DEFAULT_REGION=us-east-1
cdk synth          # safe: no AWS changes
# cdk deploy       # NOT YET: wait for account confirmation
```

Naming: `smartvibes-songwriter-<env>-<resource>` (default env `dev`, override with `-c env=prod`).
Stateful resources (DynamoDB table, Cognito user pool) use `RETAIN`.

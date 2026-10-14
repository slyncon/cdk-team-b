# cdk-team-b

The medical-documents team's independent Python AWS CDK v2 application for the Partenamut
Developer Enablement case. It consumes a tagged release of the **cdk-launchpad**
package, imports `cdk_launchpad.constructs`, and owns only its stack, handler,
fixtures, tests, and project/CI settings. Shared implementations are not copied.

```text
team S3 bucket → incoming/*.json notification → team Python Lambda → application logs
```

This separate application demonstrates onboarding a second team without changing
Platform code. It has its own stack and handler and no Claims resource references.

## Setup and immutable Platform dependency

Platform 0.1.2 is pinned to a full source commit in requirements.txt. This upgrade
adds generic AWS naming validation and the TLS template gate; application constructs
and resource IDs remain unchanged. No shared source is copied into this repository.

Prerequisites: Python 3.12, Node 24 LTS/npm, Git; AWS CLI v2 for human AWS operations.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
npm ci
export PATH="$PWD/node_modules/.bin:$PATH"
python -m ruff check .
python -m pytest -q
python -m bandit -r handler app.py stack.py scripts -ll
python -m pip_audit
npm audit --audit-level=high
cdk ls
cdk synth
cdk-launchpad-validate .build/cdk.out
```

GitHub Actions runs tests/lint, Gitleaks, Python/dependency scans, synthesis and the
shared security validator. It has no AWS credentials and never deploys or bootstraps.
The final interview workflow is automated CI with manual CD for both teams.
Wait for Validate team to pass, review the diff, then deploy the same reviewed commit.

The installed validator checks all actual application buckets for encryption,
public-access blocks and TLS, plus generic AWS identities/names/tags, including
raw resources bypassing SecureBucket. Both team repositories and local paths keep
their existing names. Version adoption is explicit; never replace a full commit
with an automatically moving main branch.

## Security demonstration and branch protection

```bash
python scripts/security_demo.py secure
cdk-launchpad-validate .build/security-demo

python scripts/security_demo.py insecure
cdk-launchpad-validate .build/security-demo
```

The first gate passes; the second deliberately fails. Correct by rerunning the
`secure` mode and its gate. The script only synthesizes ignored demo files; it
never changes the application's stack or deploys resources. Never deploy
`SecurityDemo`. Negative unit tests pass by asserting that insecure input is rejected.

For an actual failing PR check, temporarily append this step to the workflow on
a demonstration branch:

```yaml
      - name: Demonstrate insecure bucket rejection
        run: |
          python scripts/security_demo.py insecure
          cdk-launchpad-validate .build/security-demo
```

Push/open the PR yourself, observe `Validate team` fail, then change `insecure`
to `secure` and push the correction to show green. Remove the temporary step after
the demonstration. Keep the normal deployed application unchanged.

After the first hosted run, configure `main` protection to require PRs, review,
and the `Validate team` status check with current passing checks. Restrict bypass,
force pushes, and deletion where supported. GitHub Free supports protection and
free standard hosted runners for public repositories; private plan limits differ.
These rules are recommendations, not already configured. See
[protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
and [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Manual AWS deployment

Use IAM Identity Center profile `cdk-sso`, account `117301763389` and region
`eu-central-1`. Both teams deploy manually after successful CI. Check sandbox
billing/budget; small fixtures and short application log retention do not guarantee
no charges. All commands below are human-operated. Set your personal profile and region first:

```bash
aws sso login --profile cdk-sso
export AWS_REGION=eu-central-1
export AWS_DEFAULT_REGION=eu-central-1
aws sts get-caller-identity --profile cdk-sso

cdk synth --profile cdk-sso
cdk-launchpad-validate .build/cdk.out

# Only if this account/region needs CDK bootstrap resources; skip if already ready.
cdk bootstrap aws://117301763389/eu-central-1 --profile cdk-sso --termination-protection

cdk diff MedicalDocumentsTeamStack --profile cdk-sso --change-set false
cdk deploy MedicalDocumentsTeamStack --profile cdk-sso
```

Confirm the expected account/region. Review the diff and permission prompt. Stop
if an existing bucket would be replaced/deleted or the diff contains unexpected
changes; do not destroy a deployed stack to migrate directories. Keep stack names,
construct IDs, CDK feature flags, dependency pins, and handler assets stable during
migration. CloudFormation outputs provide actual resource names.

```bash
MEDICAL_BUCKET=$(aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue | [0]" --output text \
  --profile cdk-sso --region eu-central-1)
MEDICAL_LOG_GROUP=$(aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query "Stacks[0].Outputs[?OutputKey=='LogGroupName'].OutputValue | [0]" --output text \
  --profile cdk-sso --region eu-central-1)

aws s3 cp fixtures/medical_document.json "s3://$MEDICAL_BUCKET/incoming/medical_document.json" \
  --profile cdk-sso --region eu-central-1
aws logs tail "$MEDICAL_LOG_GROUP" --since 10m \
  --profile cdk-sso --region eu-central-1
```

Stop if an output is empty or `None`. Notifications are asynchronous; wait briefly
and repeat log reads as needed. The log contains team `medical-documents`, a synthetic document
ID, and `result: processed`. Inputs are fictional JSON metadata, not actual health
or insurance records. Processing means read/validate/log, not claim approval or
payment. The handler never writes S3 objects, and duplicate events are safe to
repeat. Durable retries/dead-letter handling are outside this phase.

## Manual cleanup

Migration does not require cleanup of the existing stack. When deliberately
finishing the disposable demo, verify identity and the bucket's actual stack output,
then list its contents before any deletion:

```bash
aws sts get-caller-identity --profile cdk-sso
aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query 'Stacks[0].Outputs' --output table \
  --profile cdk-sso --region eu-central-1
aws s3 ls "s3://$MEDICAL_BUCKET/" --recursive \
  --profile cdk-sso --region eu-central-1
```

Only after confirming this is the disposable demo bucket:

```bash
aws s3 rm "s3://$MEDICAL_BUCKET/" --recursive \
  --profile cdk-sso --region eu-central-1
cdk destroy MedicalDocumentsTeamStack --profile cdk-sso
```

Empty the bucket before deletion. `DESTROY` is demo-only and automatic object
deletion is disabled; meaningful data would normally merit `RETAIN`. Application
log groups are removed with the stack. Do not destroy shared `CDKToolkit`;
bootstrap assets and notification-helper logs follow the sandbox owner's lifecycle.

Future automated deployment is proposed, not active. It could use protected workflows
and GitHub OIDC with narrowly scoped AWS roles and approvals. No OIDC, AWS keys,
Secrets, or deployment automation are implemented in this phase.

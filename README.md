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

## Setup and versioned Platform dependency

Prerequisites: Python 3.12, Node 24 LTS/npm, Git; AWS CLI v2 only for manual AWS work.
Both teams consume the Platform repository at the same tested release:

```text
cdk-launchpad @ git+https://github.com/slyncon/partenamut-cdk-use-case.git@b5658184165e16aeac462114a229636ba29b23f7
```

The Python distribution is `cdk-launchpad`; its imports use `cdk_launchpad`.
No package registry, AWS credentials, or GitHub Secrets are needed to install a
public tagged source dependency. Platform 0.1.0 is pinned to its full source commit. Team A pilots automated
deployment with 0.1.1; this team retains validation-only CI and manual deployment.
CI actions are pinned and validation includes secret, code, and dependency scans.
The dependency is a regular installation from the Platform release, independent
of sibling directories. Local environments and generated assets are ignored by Git.

From this project's root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
npm ci
export PATH="$PWD/node_modules/.bin:$PATH"
```

Each repository owns its environment, test/lint settings, and pinned CDK CLI
(`2.1145.0`). The Platform dependency pins the compatible Python CDK library.
To upgrade independently, change this team's ref to a newly published tag such
as `@v0.1.1`, run `python -m pip install --upgrade -r requirements.txt`, then rerun
all checks and the live diff. Other teams keep their chosen version.

## Offline checks and CI

```bash
python -m ruff check .
python -m pytest -q
cdk synth
cdk-launchpad-validate .build/cdk.out
```

These commands require no AWS credentials or resource lookups. The CLI saves the
CloudFormation template and handler assets in `.build/cdk.out/`. A configured
profile may cause read-only account-resolution calls locally. CI sets empty AWS
configuration paths and disables metadata discovery without authenticating to AWS.

`.github/workflows/ci.yml` runs these steps on PRs targeting `main` and pushes to
`main`, using Python 3.12, Node 24, standard Ubuntu runners and `contents: read`.
It installs the pinned tagged Platform dependency and never deploys. Check the repository Actions tab for the hosted result.

Tests mock boto3 reads, reject invalid JSON/fields, verify repeat-safe behavior,
assert platform consumption and notification/resource identities, and exercise
secure/insecure synthesized templates through the installed shared validator.
The validator checks every S3 bucket, including raw buckets bypassing the shared
construct; violations exit 1 with resource-specific messages.

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

Use an authenticated profile for your personal AWS account and the selected
deployment region. This team remains manual; Team A is the OIDC deployment pilot. Check sandbox
billing/budget; small fixtures and short application log retention do not guarantee
no charges. All commands below are human-operated. Set your personal profile and region first:

```bash
export PERSONAL_AWS_PROFILE="<your-personal-account-profile>"
export AWS_REGION="<your-deployment-region>"
export AWS_DEFAULT_REGION="$AWS_REGION"
aws sts get-caller-identity --profile "$PERSONAL_AWS_PROFILE"

cdk synth --profile "$PERSONAL_AWS_PROFILE"
cdk-launchpad-validate .build/cdk.out

# Only if this account/region needs CDK bootstrap resources; skip if already ready.
cdk bootstrap --profile "$PERSONAL_AWS_PROFILE"

cdk diff MedicalDocumentsTeamStack --profile "$PERSONAL_AWS_PROFILE"
cdk deploy MedicalDocumentsTeamStack --profile "$PERSONAL_AWS_PROFILE"
```

Confirm the expected account/region. Review the diff and permission prompt. Stop
if an existing bucket would be replaced/deleted or the diff contains unexpected
changes; do not destroy a deployed stack to migrate directories. Keep stack names,
construct IDs, CDK feature flags, dependency pins, and handler assets stable during
migration. CloudFormation outputs provide actual resource names.

```bash
MEDICAL_BUCKET=$(aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue | [0]" --output text \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION")
MEDICAL_LOG_GROUP=$(aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query "Stacks[0].Outputs[?OutputKey=='LogGroupName'].OutputValue | [0]" --output text \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION")

aws s3 cp fixtures/medical_document.json "s3://$MEDICAL_BUCKET/incoming/medical_document.json" \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION"
aws logs tail "$MEDICAL_LOG_GROUP" --since 10m \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION"
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
aws sts get-caller-identity --profile "$PERSONAL_AWS_PROFILE"
aws cloudformation describe-stacks --stack-name MedicalDocumentsTeamStack \
  --query 'Stacks[0].Outputs' --output table \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION"
aws s3 ls "s3://$MEDICAL_BUCKET/" --recursive \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION"
```

Only after confirming this is the disposable demo bucket:

```bash
aws s3 rm "s3://$MEDICAL_BUCKET/" --recursive \
  --profile "$PERSONAL_AWS_PROFILE" --region "$AWS_REGION"
cdk destroy MedicalDocumentsTeamStack --profile "$PERSONAL_AWS_PROFILE"
```

Empty the bucket before deletion. `DESTROY` is demo-only and automatic object
deletion is disabled; meaningful data would normally merit `RETAIN`. Application
log groups are removed with the stack. Do not destroy shared `CDKToolkit`;
bootstrap assets and notification-helper logs follow the sandbox owner's lifecycle.

Future automated deployment could use separate protected GitHub Actions workflows
and GitHub OIDC with narrowly scoped AWS roles and approvals. No OIDC, AWS keys,
Secrets, or deployment automation are implemented in this phase.

"""Medical Documents team's independent CDK application."""

import os

from aws_cdk import App, Environment

from stack import MedicalDocumentsTeamStack

app = App()
MedicalDocumentsTeamStack(
    app,
    "MedicalDocumentsTeamStack",
    env=Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)
app.synth()

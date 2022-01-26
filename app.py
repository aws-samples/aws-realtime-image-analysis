#!/usr/bin/env python3
import os

from aws_cdk import core

from image_insights.image_insights_stack import ImageInsightsStack


ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT', '')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
AWS_ENV = core.Environment(account=ACCOUNT, region=REGION)

app = core.App()
ImageInsightsStack(app, "image-insights", env=AWS_ENV)

app.synth()

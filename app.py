#!/usr/bin/env python3
import os

import aws_cdk as cdk

from image_insights.image_insights_stack import ImageInsightsStack


ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT', '')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
AWS_ENV = cdk.Environment(account=ACCOUNT, region=REGION)

app = cdk.App()
ImageInsightsStack(app, "image-insights", env=AWS_ENV)

app.synth()

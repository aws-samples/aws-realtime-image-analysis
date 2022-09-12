#!/usr/bin/env python3
import os

import aws_cdk as cdk

from image_insights import (
  ImageInsightsVpcStack,
  ImageInsightsS3Stack,
  ImageInsightsApiGwStack,
  ImageInsightsKinesisStreamStack,
  ImageTaggerTriggerLambdaStack,
  BastionHostStack,
  ImageInsightsElasticsearchStack,
  ImageTaggerLambdaStack
)


AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"])

app = cdk.App()

vpc_stack = ImageInsightsVpcStack(app, "ImageInsightsVpc", env=AWS_ENV)

s3_stack = ImageInsightsS3Stack(app, "ImageInsightsS3")

api_gw_stack = ImageInsightsApiGwStack(app, "ImageInsightsApiGw")

kds_stack = ImageInsightsKinesisStreamStack(app, "ImageInsightsKinesisStream")

image_tagger_trigger_lambda = ImageTaggerTriggerLambdaStack(app,
  "ImageInsightsImageTaggerTriggerLambda",
  s3_stack.s3_input_bucket,
  kds_stack.kinesis_stream
)

bastion_host = BastionHostStack(app, "ImageInsightsBastionHost",
  vpc_stack.vpc,
  env=AWS_ENV
)

image_tag_search_stack = ImageInsightsElasticsearchStack(app,
  "ImageInsightsElasticsearch",
  vpc_stack.vpc,
  bastion_host.sg_bastion_host,
  env=AWS_ENV
)

image_tagger_lambda = ImageTaggerLambdaStack(app,
  "ImageInsightsImageTaggerLambda",
  vpc_stack.vpc,
  image_tag_search_stack.domain_endpoint,
  image_tag_search_stack.sg_search_client,
  kds_stack.kinesis_stream,
  env=AWS_ENV
)

app.synth()

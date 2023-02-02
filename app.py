#!/usr/bin/env python3
import os

import aws_cdk as cdk

from image_insights import (
  ImageInsightsVpcStack,
  ImageInsightsS3Stack,
  ImageInsightsApiGwStack,
  ImageInsightsKinesisStreamStack,
  ImageTaggerTriggerLambdaStack,
  ImageTaggerLambdaS3EventSourceStack,
  BastionHostStack,
  # ImageInsightsElasticsearchStack,
  ImageInsightsOpenSearchStack,
  ImageTaggerLambdaStack
)


AWS_ENV = cdk.Environment(
  account=os.environ["CDK_DEFAULT_ACCOUNT"],
  region=os.environ["CDK_DEFAULT_REGION"])

app = cdk.App()

vpc_stack = ImageInsightsVpcStack(app, "ImageInsightsVpc", env=AWS_ENV)

s3_stack = ImageInsightsS3Stack(app, "ImageInsightsS3")
s3_stack.add_dependency(vpc_stack)

api_gw_stack = ImageInsightsApiGwStack(app, "ImageInsightsApiGw")
api_gw_stack.add_dependency(s3_stack)

kds_stack = ImageInsightsKinesisStreamStack(app, "ImageInsightsKinesisStream")
kds_stack.add_dependency(vpc_stack)

image_tagger_trigger_lambda = ImageTaggerTriggerLambdaStack(app,
  "ImageInsightsImageTaggerTriggerLambda",
  kds_stack.kinesis_stream
)
image_tagger_trigger_lambda.add_dependency(kds_stack)

lambda_s3_event_source = ImageTaggerLambdaS3EventSourceStack(app,
  "ImageInsightsLambdaS3EventSource",
  s3_stack.s3_input_bucket,
  image_tagger_trigger_lambda.lambda_fn
)
lambda_s3_event_source.add_dependency(image_tagger_trigger_lambda)
lambda_s3_event_source.add_dependency(s3_stack)

bastion_host = BastionHostStack(app, "ImageInsightsBastionHost",
  vpc_stack.vpc,
  env=AWS_ENV
)
bastion_host.add_dependency(vpc_stack)

image_tag_search_stack = ImageInsightsOpenSearchStack(app,
  "ImageInsightsSearch",
  vpc_stack.vpc,
  bastion_host.sg_bastion_host,
  env=AWS_ENV
)

# image_tag_search_stack = ImageInsightsElasticsearchStack(app,
#   "ImageInsightsElasticsearch",
#   vpc_stack.vpc,
#   bastion_host.sg_bastion_host,
#   env=AWS_ENV
# )
image_tag_search_stack.add_dependency(bastion_host)

image_tagger_lambda = ImageTaggerLambdaStack(app,
  "ImageInsightsImageTaggerLambda",
  vpc_stack.vpc,
  image_tag_search_stack.search_domain_endpoint,
  image_tag_search_stack.sg_search_client,
  kds_stack.kinesis_stream,
  env=AWS_ENV
)
image_tagger_lambda.add_dependency(image_tag_search_stack)
image_tagger_lambda.add_dependency(lambda_s3_event_source)

app.synth()

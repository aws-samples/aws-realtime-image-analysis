# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
  aws_iam,
  aws_lambda as _lambda,
  aws_logs
)
from constructs import Construct

from aws_cdk.aws_lambda_event_sources import (
  S3EventSource
)

class ImageTaggerTriggerLambdaStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, img_kinesis_stream, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # create lambda function
    trigger_img_tagger_lambda_fn = _lambda.Function(self, "TriggerImageAutoTagger",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="TriggerImageAutoTagger",
      handler="trigger_image_auto_tagger.lambda_handler",
      description="Trigger to recognize an image in S3",
      code=_lambda.Code.from_asset("./src/main/python/TriggerImageAutoTagger"),
      environment={
        'REGION_NAME': cdk.Aws.REGION,
        'KINESIS_STREAM_NAME': img_kinesis_stream.stream_name
      },
      timeout=cdk.Duration.minutes(5)
    )

    trigger_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[img_kinesis_stream.stream_arn],
      actions=["kinesis:Get*",
        "kinesis:List*",
        "kinesis:Describe*",
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ]
    ))

    #XXX: https://github.com/aws/aws-cdk/issues/2240
    # To avoid to create extra Lambda Functions with names like LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a
    # if log_retention=aws_logs.RetentionDays.THREE_DAYS is added to the constructor props
    log_group = aws_logs.LogGroup(self, "TriggerImageAutoTaggerLogGroup",
      log_group_name="/aws/lambda/TriggerImageAutoTagger",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(trigger_img_tagger_lambda_fn)

    self.lambda_fn = trigger_img_tagger_lambda_fn

    cdk.CfnOutput(self, '{self.stack_name}_LambdaFunctionName', value=self.lambda_fn.function_name)


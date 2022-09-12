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
  KinesisEventSource
)


class ImageTaggerLambdaStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, search_domain_endpoint, sg_search_client, img_kinesis_stream, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXX: https://github.com/aws/aws-cdk/issues/1342
    s3_lib_bucket_name = self.node.try_get_context('lib_bucket_name')
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, construct_id, s3_lib_bucket_name)
    es_lib_layer = _lambda.LayerVersion(self, "ESLib",
      layer_version_name="es-lib",
      compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
      code=_lambda.Code.from_bucket(s3_lib_bucket, "var/es-lib.zip")
    )

    #XXX: Deploy lambda in VPC - https://github.com/aws/aws-cdk/issues/1342
    auto_img_tagger_lambda_fn = _lambda.Function(self, "AutomaticImageTagger",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="AutomaticImageTagger",
      handler="image_auto_tagger.lambda_handler",
      description="Automatically tag images",
      code=_lambda.Code.from_asset("./src/main/python/ImageAutoTagger"),
      environment={
        # 'ES_HOST': es_cfn_domain.attr_domain_endpoint,
        'ES_HOST': search_domain_endpoint,
        'ES_INDEX': 'image_insights',
        'ES_TYPE': 'photo'
      },
      timeout=cdk.Duration.minutes(5),
      layers=[es_lib_layer],
      security_groups=[sg_search_client],
      vpc=vpc
    )

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["rekognition:*"]))

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["s3:Get*", "s3:List*"]))

    img_kinesis_event_source = KinesisEventSource(img_kinesis_stream, batch_size=100, starting_position=_lambda.StartingPosition.LATEST)
    auto_img_tagger_lambda_fn.add_event_source(img_kinesis_event_source)

    log_group = aws_logs.LogGroup(self, "AutomaticImageTaggerLogGroup",
      log_group_name="/aws/lambda/AutomaticImageTagger",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(auto_img_tagger_lambda_fn)


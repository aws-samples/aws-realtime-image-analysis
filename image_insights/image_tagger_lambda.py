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

  def __init__(self, scope: Construct, construct_id: str, vpc, search_domain_endpoint, search_domain_arn, sg_search_client, img_kinesis_stream, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXX: https://github.com/aws/aws-cdk/issues/1342
    s3_lib_bucket_name = self.node.try_get_context('lib_bucket_name')
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, construct_id, s3_lib_bucket_name)
    es_lib_layer = _lambda.LayerVersion(self, "ESLib",
      layer_version_name="es-lib",
      compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
      code=_lambda.Code.from_bucket(s3_lib_bucket, "var/es-lib.zip")
    )

    ES_INDEX_NAME = 'image_insights'
    ES_TYPE_NAME = 'photo'

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
        'ES_INDEX': ES_INDEX_NAME,
        'ES_TYPE': ES_TYPE_NAME
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

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[search_domain_arn, "{}/*".format(search_domain_arn)],
      actions=["es:DescribeElasticsearchDomain",
        "es:DescribeElasticsearchDomains",
        "es:DescribeElasticsearchDomainConfig",
        "es:ESHttpPost",
        "es:ESHttpPut"]
    ))

    auto_img_tagger_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      #XXX: https://aws.amazon.com/premiumsupport/knowledge-center/kinesis-data-firehose-delivery-failure/
      resources=[
        search_domain_arn,
        f"{search_domain_arn}/_all/_settings",
        f"{search_domain_arn}/_cluster/stats",
        f"{search_domain_arn}/{ES_INDEX_NAME}*/_mapping/{ES_TYPE_NAME}",
        f"{search_domain_arn}/_nodes",
        f"{search_domain_arn}/_nodes/stats",
        f"{search_domain_arn}/_nodes/*/stats",
        f"{search_domain_arn}/_stats",
        f"{search_domain_arn}/{ES_INDEX_NAME}*/_stats"
      ],
      actions=["es:ESHttpGet"]
    ))

    log_group = aws_logs.LogGroup(self, "AutomaticImageTaggerLogGroup",
      log_group_name="/aws/lambda/AutomaticImageTagger",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(auto_img_tagger_lambda_fn)

    cdk.CfnOutput(self, '{self.stack_name}_LambdaFunctionName', value=auto_img_tagger_lambda_fn.function_name)
    cdk.CfnOutput(self, f'{self.stack_name}_LambdaRoleArn', value=auto_img_tagger_lambda_fn.role.role_arn)


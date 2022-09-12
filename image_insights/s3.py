# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3
)
from constructs import Construct


class ImageInsightsS3Stack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    s3_image_bucket_name_suffix = self.node.try_get_context('image_bucket_name_suffix')
    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name="image-insights-{region}-{suffix}".format(region=cdk.Aws.REGION, suffix=s3_image_bucket_name_suffix))

    s3_bucket.add_cors_rule(allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.POST],
      allowed_origins=['*'],
      allowed_headers=['Authorization'],
      max_age=3000
    )

    self.s3_input_bucket = s3_bucket

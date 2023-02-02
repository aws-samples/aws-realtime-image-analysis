# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_kinesis as kinesis
)
from constructs import Construct


class ImageInsightsKinesisStreamStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    img_kinesis_stream = kinesis.Stream(self, "ImageAutoTaggerUploadedImagePath",
      stream_name="image-auto-tagger-img",
      # ON-DEMAND capacity mode: the stream will autoscale and 
      # be billed according to the volume of data ingested and retrieved
      stream_mode=kinesis.StreamMode.ON_DEMAND)

    self.kinesis_stream = img_kinesis_stream

    cdk.CfnOutput(self, '{self.stack_name}_KinesisStreamArn',
      value=self.kinesis_stream.stream_arn)


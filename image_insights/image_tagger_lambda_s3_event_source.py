# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3
)
from constructs import Construct

from aws_cdk.aws_lambda_event_sources import (
  S3EventSource
)

class ImageTaggerLambdaS3EventSourceStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, s3_bucket, lambda_fn, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # assign notification for the s3 event type (ex: OBJECT_CREATED)
    for suffix in ('.jpeg', 'png'):
      s3_event_filter = s3.NotificationKeyFilter(prefix="raw-image/", suffix=suffix)
      s3_event_source = S3EventSource(s3_bucket, events=[s3.EventType.OBJECT_CREATED], filters=[s3_event_filter])
      lambda_fn.add_event_source(s3_event_source)


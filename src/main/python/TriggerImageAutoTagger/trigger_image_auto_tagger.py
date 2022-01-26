#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import json
import os
import urllib.parse
import traceback
import datetime

import boto3

DRY_RUN = (os.getenv('DRY_RUN', 'false') == 'true')

AWS_REGION = os.getenv('REGION_NAME', 'us-east-1')
KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME', 'november-photo')


def write_records_to_kinesis(kinesis_client, kinesis_stream_name, records):
  import random
  random.seed(47)

  def gen_records():
    record_list = []
    for rec in records:
      payload = json.dumps(rec, ensure_ascii=False)
      partition_key = 'part-{:05}'.format(random.randint(1, 1024))
      record_list.append({'Data': payload, 'PartitionKey': partition_key})
    return record_list

  MAX_RETRY_COUNT = 3

  record_list = gen_records()
  for _ in range(MAX_RETRY_COUNT):
    try:
      response = kinesis_client.put_records(Records=record_list, StreamName=kinesis_stream_name)
      print("[DEBUG] try to write_records_to_kinesis", response, file=sys.stderr)
      break
    except Exception as ex:
      import time

      traceback.print_exc()
      time.sleep(2)
  else:
    raise RuntimeError('[ERROR] Failed to put_records into kinesis stream: {}'.format(kinesis_stream_name))


def lambda_handler(event, context):
  kinesis_client = boto3.client('kinesis', region_name=AWS_REGION)

  for record in event['Records']:
    try:
      bucket = record['s3']['bucket']['name']
      key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')

      record = {'s3_bucket': bucket, 's3_key': key}
      print("[INFO] object created: ", record, file=sys.stderr)
      write_records_to_kinesis(kinesis_client, KINESIS_STREAM_NAME, [record])
    except Exception as ex:
      traceback.print_exc()


if __name__ == '__main__':
  s3_event = '''{
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "1970-01-01T00:00:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "127.0.0.1"
      },
      "responseElements": {
        "x-amz-request-id": "EXAMPLE123456789",
        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "testConfigRule",
        "bucket": {
          "name": "november-photo",
          "ownerIdentity": {
            "principalId": "EXAMPLE"
          },
          "arn": "arn:aws:s3:::november-photo"
        },
        "object": {
          "key": "raw-image/20191120_122332.jpg",
          "size": 4300,
          "eTag": "bca44a2aac2c789bc77b5eb13bcb04e2",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}'''

  event = json.loads(s3_event)
  lambda_handler(event, {})


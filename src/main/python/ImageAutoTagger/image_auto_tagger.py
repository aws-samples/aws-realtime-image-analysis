#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import json
import base64
import os
import traceback
import hashlib
import datetime

import boto3
from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection
from requests_aws4auth import AWS4Auth

S3_URL_FMT = 'https://{bucket_name}.s3.amazonaws.com/{object_key}'

AWS_REGION = os.getenv('REGION_NAME', 'us-east-1')

ES_INDEX, ES_TYPE = (os.getenv('ES_INDEX', 'november_photo'), os.getenv('ES_TYPE', 'photo'))
ES_HOST = os.getenv('ES_HOST')

session = boto3.Session(region_name=AWS_REGION)
credentials = session.get_credentials()
credentials = credentials.get_frozen_credentials()
access_key = credentials.access_key
secret_key = credentials.secret_key
token = credentials.token

aws_auth = AWS4Auth(
  access_key,
  secret_key,
  AWS_REGION,
  'es',
  session_token=token
)

es_client = Elasticsearch(
  hosts = [{'host': ES_HOST, 'port': 443}],
  http_auth=aws_auth,
  use_ssl=True,
  verify_certs=True,
  connection_class=RequestsHttpConnection
)
print('[INFO] ElasticSearch Service', json.dumps(es_client.info(), indent=2), file=sys.stderr)


def _report_detected_labels(photo, response):
  print('Detected labels for ' + photo)
  print()
  for label in response['Labels']:
    print ("Label: " + label['Name'])
    print ("Confidence: " + str(label['Confidence']))
    print ("Instances:")
    for instance in label['Instances']:
      print ("  Bounding box")
      print ("    Top: " + str(instance['BoundingBox']['Top']))
      print ("    Left: " + str(instance['BoundingBox']['Left']))
      print ("    Width: " +  str(instance['BoundingBox']['Width']))
      print ("    Height: " +  str(instance['BoundingBox']['Height']))
      print ("  Confidence: " + str(instance['Confidence']))
      print()

    print ("Parents:")
    for parent in label['Parents']:
      print ("   " + parent['Name'])
    print ("----------")
    print ()


def lambda_handler(event, context):
  doc_list = []

  for record in event['Records']:
    try:
      payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
      json_data = json.loads(payload)

      bucket, photo = (json_data['s3_bucket'], json_data['s3_key'])
      rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)

      response = rekognition_client.detect_labels(Image={'S3Object':{'Bucket': bucket, 'Name': photo}},
          MaxLabels=10)
      #_report_detected_labels(photo, response)

      lables = sorted([label['Name'] for label in response['Labels']])
      tags = ', '.join(lables)
      tag_id = hashlib.md5(tags.encode('utf-8')).hexdigest()[:8]

      image_id = os.path.basename(photo)
      doc = {
        'doc_id': hashlib.md5(image_id.encode('utf-8')).hexdigest()[:8],
        'image_id': image_id,
        'image_url': S3_URL_FMT.format(bucket_name=bucket, object_key=photo),
        #'tags': tags,
        'tags': lables,
        'tag_id': tag_id,
        'created_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
      }
      #print('[INFO]', doc)

      es_index_action_meta = {"index": {"_index": ES_INDEX, "_type": ES_TYPE, "_id": doc['doc_id']}}
      doc_list.append(es_index_action_meta)
      doc_list.append(doc)
    except Exception as ex:
      traceback.print_exc()

  if not doc_list:
    return

  try:
    es_bulk_body = '\n'.join([json.dumps(e) for e in doc_list])
    res = es_client.bulk(body=es_bulk_body, index=ES_INDEX, refresh=True)
  except Exception as ex:
    traceback.print_exc()


if __name__ == "__main__":
    kinesis_data = [
      '''{"s3_bucket": "november-photo", "s3_key": "raw-image/20191119_170325.jpg"}''',
      '''{"s3_bucket": "november-photo", "s3_key": "raw-image/20191120_122332.jpg"}''',
    ]

    records = [{
      "eventID": "shardId-000000000000:49545115243490985018280067714973144582180062593244200961",
      "eventVersion": "1.0",
      "kinesis": {
        "approximateArrivalTimestamp": 1428537600,
        "partitionKey": "partitionKey-3",
        "data": base64.b64encode(e.encode('utf-8')),
        "kinesisSchemaVersion": "1.0",
        "sequenceNumber": "49545115243490985018280067714973144582180062593244200961"
      },
      "invokeIdentityArn": "arn:aws:iam::EXAMPLE",
      "eventName": "aws:kinesis:record",
      "eventSourceARN": "arn:aws:kinesis:EXAMPLE",
      "eventSource": "aws:kinesis",
      "awsRegion": "us-east-1"
      } for e in kinesis_data]

    event = {"Records": records}
    lambda_handler(event, {})

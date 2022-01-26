#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

#***************************************************************************************/
#*
#*  Author: Beomi
#*  Availability: https://gist.github.com/Beomi/ac9d34dbfa9a6bdaf4a0426e8b83b4e3
#*  SPDX-License-Identifier: MIT
#*
#***************************************************************************************/

import base64
import hashlib
import hmac
import json
import logging
import os

logger = logging.getLogger()
if len(logger.handlers) > 0:
  # The Lambda environment pre-configures a handler logging to stderr.
  # If a handler is already configured, `.basicConfig` does not execute.
  # Thus we set the level directly.
  logger.setLevel(logging.INFO)
else:
  logging.basicConfig(level=logging.INFO)

ACCESS_KEY = os.environ.get('ACCESS_KEY')
SECRET_KEY = os.environ.get('SECRET_KEY')


# Key derivation functions. See:
# http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
def sign(key, msg):
  return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def getSignatureKey(key, date_stamp, regionName, serviceName):
  kDate = sign(('AWS4' + key).encode('utf-8'), date_stamp)
  kRegion = sign(kDate, regionName)
  kService = sign(kRegion, serviceName)
  kSigning = sign(kService, 'aws4_request')
  return kSigning


def sign_policy(policy, credential):
  """ Sign and return the policy document for a simple upload.
  http://aws.amazon.com/articles/1434/#signyours3postform """
  base64_policy = base64.b64encode(policy)
  parts = credential.split('/')
  date_stamp = parts[1]
  region = parts[2]
  service = parts[3]

  signedKey = getSignatureKey(SECRET_KEY, date_stamp, region, service)
  signature = hmac.new(signedKey, base64_policy, hashlib.sha256).hexdigest()

  base64_policy = base64_policy.decode('utf-8')
  return {'policy': base64_policy, 'signature': signature}


def sign_headers(headers):
  """ Sign and return the headers for a chunked upload. """
  # headers = str(bytearray(headers, 'utf-8'))  # hmac doesn't want unicode
  parts = headers.split('\n')
  canonical_request = ('\n'.join(parts[3:]))
  algorithm = parts[0]
  amz_date = parts[1]
  credential_scope = parts[2]
  string_to_sign = "\n".join([algorithm, amz_date, credential_scope,
    hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()])

  cred_parts = credential_scope.split('/')
  date_stamp = cred_parts[0]
  region = cred_parts[1]
  service = cred_parts[2]
  signed_key = getSignatureKey(SECRET_KEY, date_stamp, region, service)
  signature = hmac.new(signed_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

  return {'signature': signature}


def lambda_handler(event, context):
  """ Route for signing the policy document or REST headers. """

  logger.info('event: %s' % event)
  request_payload = event
  if request_payload.get('headers'):
    response_data = sign_headers(request_payload['headers'])
  else:
    credential = list([c for c in request_payload['conditions'] if 'x-amz-credential' in c][0].values())[0]
    logger.info('credential=%s, data_type=%s' % (credential, type(credential)))
    response_data = sign_policy(json.dumps(event).encode('utf-8'), str(credential))
  return response_data


if __name__ == '__main__':
  import pprint

  ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
  SECRET_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'

  event = {
    'expiration': '2020-11-18T09:18:59.290Z',
     'conditions': [{'acl': 'private'},
                    {'bucket': 'image-insights-us-east-1-zy2wbzt'},
                    {'Content-Type': 'image/jpeg'},
                    {'success_action_status': '200'},
                    {'x-amz-algorithm': 'AWS4-HMAC-SHA256'},
                    {'key': 'raw-image/img7.jpeg'},
                    {'x-amz-credential': 'AKIAIOSFODNN7EXAMPLE/20201118/us-east-1/s3/aws4_request'},
                    {'x-amz-date': '20201118T091359Z'},
                    {'x-amz-meta-qqfilename': 'sample_image.jpeg'}]
  }

  res = lambda_handler(event, {})
  pprint.pprint(res)


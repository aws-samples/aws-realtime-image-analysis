# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_apigateway as apigw,
  aws_iam,
  aws_lambda as _lambda,
  aws_logs,
)
from constructs import Construct


class ImageInsightsApiGwStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    s3_access_key_id = self.node.try_get_context('s3_access_key_id')
    s3_secret_key = self.node.try_get_context('s3_secret_key')
    sign_s3_post_lambda_fn = _lambda.Function(self, "SignS3Post",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="SignS3Post",
      handler="sign_s3_post.lambda_handler",
      description="Return Signature4 for S3",
      code=_lambda.Code.from_asset("./src/main/python/SignS3Post"),
      environment={
        'ACCESS_KEY': s3_access_key_id,
        'SECRET_KEY': s3_secret_key
      },
      timeout=cdk.Duration.minutes(5)
    )
    log_group = aws_logs.LogGroup(self, "SignS3PostLogGroup",
      log_group_name="/aws/lambda/SignS3Post",
      removal_policy=cdk.RemovalPolicy.DESTROY, #XXX: for testing
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(sign_s3_post_lambda_fn)

    api = apigw.RestApi(self, "ImageAutoTaggerUploader",
      rest_api_name="ImageAutoTaggerUploader",
      description="This service serves uploading images into s3.",
      endpoint_types=[apigw.EndpointType.REGIONAL],
      binary_media_types=["image/png", "image/jpg", "image/jpeg"],
      deploy=True,
      deploy_options=apigw.StageOptions(stage_name="v1")
    )

    rest_api_role = aws_iam.Role(self, "ApiGatewayRoleForS3",
      role_name="ApiGatewayRoleForS3FullAccess",
      assumed_by=aws_iam.ServicePrincipal("apigateway.amazonaws.com"),
      managed_policies=[aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")]
    )

    list_objects_responses = [apigw.IntegrationResponse(status_code="200",
        #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationResponse.html#aws_cdk.aws_apigateway.IntegrationResponse.response_parameters
        # The response parameters from the backend response that API Gateway sends to the method response.
        # Use the destination as the key and the source as the value:
        #  - The destination must be an existing response parameter in the MethodResponse property.
        #  - The source must be an existing method request parameter or a static value.
        response_parameters={
          'method.response.header.Timestamp': 'integration.response.header.Date',
          'method.response.header.Content-Length': 'integration.response.header.Content-Length',
          'method.response.header.Content-Type': 'integration.response.header.Content-Type'
        }
      ),
      apigw.IntegrationResponse(status_code="400", selection_pattern="4\d{2}"),
      apigw.IntegrationResponse(status_code="500", selection_pattern="5\d{2}")
    ]

    list_objects_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses
    )

    get_s3_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path='/',
      options=list_objects_integration_options
    )

    api.root.add_method("GET", get_s3_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.Model.EMPTY_MODEL
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False
      }
    )

    post_s3_lambda_integration = apigw.LambdaIntegration(sign_s3_post_lambda_fn,
     proxy=False,
     integration_responses=[{
       'statusCode': '200',
       'responseParameters': {
         'method.response.header.Access-Control-Allow-Origin': "'*'",
       }
     }]
    )

    api.root.add_method('POST',
      post_s3_lambda_integration,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Content-Type': False,
            'method.response.header.Access-Control-Allow-Origin': True
          },
          response_models={
            'application/json': apigw.Model.EMPTY_MODEL
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
    )
    self.add_cors_options(api.root)

    get_s3_folder_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses,
      #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_apigateway/IntegrationOptions.html#aws_cdk.aws_apigateway.IntegrationOptions.request_parameters
      # Specify request parameters as key-value pairs (string-to-string mappings), with a destination as the key and a source as the value.
      # The source must be an existing method request parameter or a static value.
      request_parameters={"integration.request.path.bucket": "method.request.path.folder"}
    )

    get_s3_folder_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path="{bucket}",
      options=get_s3_folder_integration_options
    )

    s3_folder = api.root.add_resource('{folder}')
    s3_folder.add_method("GET", get_s3_folder_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.Model.EMPTY_MODEL
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True
      }
    )

    get_s3_item_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=list_objects_responses,
      request_parameters={
        "integration.request.path.bucket": "method.request.path.folder",
        "integration.request.path.object": "method.request.path.item"
      }
    )

    get_s3_item_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="GET",
      path="{bucket}/{object}",
      options=get_s3_item_integration_options
    )

    s3_item = s3_folder.add_resource('{item}')
    s3_item.add_method("GET", get_s3_item_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Timestamp': False,
            'method.response.header.Content-Length': False,
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.Model.EMPTY_MODEL
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True,
        'method.request.path.item': True
      }
    )

    put_s3_item_integration_options = apigw.IntegrationOptions(
      credentials_role=rest_api_role,
      integration_responses=[apigw.IntegrationResponse(status_code="200"),
        apigw.IntegrationResponse(status_code="400", selection_pattern="4\d{2}"),
        apigw.IntegrationResponse(status_code="500", selection_pattern="5\d{2}")
      ],
      request_parameters={
        "integration.request.header.Content-Type": "method.request.header.Content-Type",
        "integration.request.path.bucket": "method.request.path.folder",
        "integration.request.path.object": "method.request.path.item"
      }
    )

    put_s3_item_integration = apigw.AwsIntegration(service="s3",
      integration_http_method="PUT",
      path="{bucket}/{object}",
      options=put_s3_item_integration_options
    )

    s3_item.add_method("PUT", put_s3_item_integration,
      authorization_type=apigw.AuthorizationType.IAM,
      api_key_required=False,
      method_responses=[apigw.MethodResponse(status_code="200",
          response_parameters={
            'method.response.header.Content-Type': False
          },
          response_models={
            'application/json': apigw.Model.EMPTY_MODEL
          }
        ),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ],
      request_parameters={
        'method.request.header.Content-Type': False,
        'method.request.path.folder': True,
        'method.request.path.item': True
      }
    )

    cdk.CfnOutput(self, '{self.stack_name}_ApiEndpoint', value=api.url)


  def add_cors_options(self, apigw_resource):
    apigw_resource.add_method('OPTIONS', apigw.MockIntegration(
        integration_responses=[{
          'statusCode': '200',
          'responseParameters': {
            # 'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'method.response.header.Access-Control-Allow-Headers': "'*'",
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'"
          }
        }],
        passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
        request_templates={"application/json":"{\"statusCode\":200}"}
      ),
      method_responses=[apigw.MethodResponse(status_code="200",
        response_parameters={
          'method.response.header.Content-Type': False,
          'method.response.header.Access-Control-Allow-Headers': True,
          'method.response.header.Access-Control-Allow-Methods': True,
          'method.response.header.Access-Control-Allow-Origin': True,
        },
        response_models={
            'application/json': apigw.Model.EMPTY_MODEL
        }),
        apigw.MethodResponse(status_code="400"),
        apigw.MethodResponse(status_code="500")
      ]
   )


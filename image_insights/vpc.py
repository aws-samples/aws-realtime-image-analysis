# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2
)
from constructs import Construct


class ImageInsightsVpcStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    #XXX: For creating this CDK Stack in the existing VPC,
    # remove comments from the below codes and
    # comments out vpc = aws_ec2.Vpc(..) codes,
    # then pass -c vpc_name=your-existing-vpc to cdk command
    # for example,
    # cdk -c vpc_name=your-existing-vpc syth
    #
    vpc_name = self.node.try_get_context('vpc_name')
    vpc = aws_ec2.Vpc.from_lookup(self, 'ExistingVPC',
      is_default=True,
      vpc_name=vpc_name
    )

    # vpc = aws_ec2.Vpc(self, "ImageInsightsVPC",
    #   cidr="10.31.0.0/21",
    #   max_azs=2,
    #   # subnet_configuration=[{
    #   #     "cidrMask": 24,
    #   #     "name": "Public",
    #   #     "subnetType": aws_ec2.SubnetType.PUBLIC,
    #   #   },
    #   #   {
    #   #     "cidrMask": 24,
    #   #     "name": "Private",
    #   #     "subnetType": aws_ec2.SubnetType.PRIVATE_WITH_NAT
    #   #   },
    #   #   {
    #   #     "cidrMask": 28,
    #   #     "name": "Isolated",
    #   #     "subnetType": aws_ec2.SubnetType.PRIVATE_ISOLATED,
    #   #     "reserved": True
    #   #   }
    #   # ],
    #   gateway_endpoints={
    #     "S3": aws_ec2.GatewayVpcEndpointOptions(
    #       service=aws_ec2.GatewayVpcEndpointAwsService.S3
    #     )
    #   }
    # )

    self.vpc = vpc

    cdk.CfnOutput(self, '{}_VPCID'.format(self.stack_name), value=self.vpc.vpc_id,
      export_name='VPCID')


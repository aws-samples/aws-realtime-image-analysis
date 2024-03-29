# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_elasticsearch
)
from constructs import Construct


class ImageInsightsElasticsearchStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, sg_bastion_host, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sg_use_es = aws_ec2.SecurityGroup(self, "ImageTagSearchClientSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for elasticsearch client of image tagger',
      security_group_name='use-image-tagger-es'
    )
    cdk.Tags.of(sg_use_es).add('Name', 'sg-use-image-tagger-es')

    sg_es = aws_ec2.SecurityGroup(self, "ImageTagSearchSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for elasticsearch of image tag',
      security_group_name='image-tagger-es'
    )
    cdk.Tags.of(sg_es).add('Name', 'sg-image-tagger-es')

    sg_es.add_ingress_rule(peer=sg_es, connection=aws_ec2.Port.all_tcp(), description='image-tagger-es')
    sg_es.add_ingress_rule(peer=sg_use_es, connection=aws_ec2.Port.all_tcp(), description='use-image-tagger-es')
    sg_es.add_ingress_rule(peer=sg_bastion_host, connection=aws_ec2.Port.all_tcp(), description='image-insights-bastion-host-sg')

    #XXX: aws cdk elastsearch example - https://github.com/aws/aws-cdk/issues/2873
    es_cfn_domain = aws_elasticsearch.CfnDomain(self, 'ImageTagSearch',
      elasticsearch_cluster_config={
        "dedicatedMasterCount": 3,
        "dedicatedMasterEnabled": True,
        "dedicatedMasterType": "t3.medium.elasticsearch",
        "instanceCount": 2,
        "instanceType": "t3.medium.elasticsearch",
        "zoneAwarenessConfig": {
          #XXX: az_count must be equal to vpc subnets count.
          "availabilityZoneCount": 2,
        },
        "zoneAwarenessEnabled": True
      },
      ebs_options={
        "ebsEnabled": True,
        "volumeSize": 10,
        "volumeType": "gp3"
      },
      domain_name="image-insights",
      elasticsearch_version="7.10",
      encryption_at_rest_options={
        "enabled": False
      },
      access_policies={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
              "AWS": "*"
            },
            "Action": [
              "es:Describe*",
              "es:List*",
              "es:Get*",
              "es:ESHttp*"
            ],
            "Resource": self.format_arn(service="es", resource="domain", resource_name="image-insights/*")
          }
        ]
      },
      #XXX: For domains running OpenSearch or Elasticsearch 5.3 and later, OpenSearch Service takes hourly automated snapshots
      # Only applies for Elasticsearch versions below 5.3
      # snapshot_options={
      #   "automatedSnapshotStartHour": 17
      # },
      vpc_options={
        "securityGroupIds": [sg_es.security_group_id],
        #XXX: az_count must be equal to vpc subnets count.
        "subnetIds": vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_NAT).subnet_ids[:2]
      }
    )
    cdk.Tags.of(es_cfn_domain).add('Name', 'image-tagger-es')

    self.domain_endpoint = es_cfn_domain.attr_domain_endpoint
    self.sg_search_client = sg_use_es

    cdk.CfnOutput(self, 'ESDomainEndpoint', value=self.domain_endpoint, export_name='ESDomainEndpoint')
    cdk.CfnOutput(self, 'ESDashboardsURL', value=f"{self.domain_endpoint}/_dashboards/", export_name='ESDashboardsURL')


from aws_cdk import (
    Stack,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_lambda as _lambda,
    custom_resources as cr,
    CustomResource,
)
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer
from constructs import Construct


class CdkEksProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        
        # 1. EKS Cluster
        
        cluster = eks.Cluster(
            self,
            "MyEKSCluster",
            version=eks.KubernetesVersion.V1_28,
            kubectl_layer=KubectlV28Layer(self, "KubectlLayer"),
            default_capacity=2,
            default_capacity_instance=ec2.InstanceType("t3.medium"),
        )

        
        # 2. SSM Parameter
        
        parameter = ssm.StringParameter(
            self,
            "MyParameter",
            parameter_name="/platform/account/env",
            string_value="development",
        )

        
        # 3. Lambda
        
        lambda_fn = _lambda.Function(
            self,
            "MyCustomLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda"),
        )

        parameter.grant_read(lambda_fn)

        
        # 4. Custom Resource
        
        provider = cr.Provider(
            self,
            "MyProvider",
            on_event_handler=lambda_fn,
        )

        custom_resource = CustomResource(
            self,
            "MyCustomResource",
            service_token=provider.service_token,
        )

        replica_count = custom_resource.get_att("replicaCount")

        
        # 5. Helm Chart
        
        cluster.add_helm_chart(
    	    "IngressNginxChart",
            chart="ingress-nginx",
    	    repository="https://kubernetes.github.io/ingress-nginx",
            release="ingress-nginx",
            namespace="default",
            values={
                "controller": {
            	    "replicaCount": replica_count
       		 }
    	    }
	)
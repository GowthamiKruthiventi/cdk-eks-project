from aws_cdk import (
    Stack,
    Token,
    Duration,
    RemovalPolicy,
    aws_eks as eks,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_lambda as _lambda,
    aws_logs as logs,
    custom_resources as cr,
    CustomResource,
)
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer
from constructs import Construct


class CdkEksProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # 0. Environment
        #    Pass at deploy time:  cdk deploy -c env=staging
        #    Falls back to "development" if not provided.
        # ------------------------------------------------------------------
        env_name = self.node.try_get_context("env") or "development"

        # ------------------------------------------------------------------
        # 1. EKS Cluster
        # ------------------------------------------------------------------
        cluster = eks.Cluster(
            self,
            "MyEKSCluster",
            version=eks.KubernetesVersion.V1_28,
            kubectl_layer=KubectlV28Layer(self, "KubectlLayer"),
            default_capacity=2,
            default_capacity_instance=ec2.InstanceType("t3.medium"),
        )

        # ------------------------------------------------------------------
        # 2. SSM Parameter
        #    Value is driven by the CDK context variable so the same stack
        #    code can be deployed for development / staging / production.
        # ------------------------------------------------------------------
        parameter = ssm.StringParameter(
            self,
            "MyParameter",
            parameter_name="/platform/account/env",
            string_value=env_name,
        )

        # ------------------------------------------------------------------
        # 3. Lambda function
        #
        #    Log group is created explicitly so retention is enforced from
        #    day one. RemovalPolicy.DESTROY ensures logs are cleaned up
        #    when the stack is destroyed.
        # ------------------------------------------------------------------
        lambda_function_name = "HelmValuesResolver"

        log_group = logs.LogGroup(
            self,
            "HelmValuesResolverLogGroup",
            log_group_name=f"/aws/lambda/{lambda_function_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        lambda_fn = _lambda.Function(
            self,
            "HelmValuesResolver",
            function_name=lambda_function_name,
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            log_group=log_group,
        )

        # Least-privilege: Lambda only read this specific SSM parameter.

        parameter.grant_read(lambda_fn)

        # ------------------------------------------------------------------
        # 4. Custom Resource
        #
        #    cr.Provider manages the full CloudFormation lifecycle
        #    (Create / Update / Delete) and handles the response protocol
        #    automatically
        # ------------------------------------------------------------------
        provider = cr.Provider(
            self,
            "MyProvider",
            on_event_handler=lambda_fn,
        )

        custom_resource = CustomResource(
            self,
            "MyCustomResource",
            service_token=provider.service_token,
            properties={
                "ForceUpdateTrigger": env_name,
            },
        )

        custom_resource.node.add_dependency(parameter)

        # get_att_string returns a CDK string token that resolves at deploy
        replica_count = Token.as_number(
            custom_resource.get_att_string("replicaCount")
        )

        # ------------------------------------------------------------------
        # 5. Helm Chart
        #    - chart version is pinned for reproducible deployments
        #    - explicit dependency ensures Helm waits for Custom Resource
        # ------------------------------------------------------------------
        helm_chart = cluster.add_helm_chart(
            "IngressNginxChart",
            chart="ingress-nginx",
            repository="https://kubernetes.github.io/ingress-nginx",
            release="ingress-nginx",
            version="4.10.1",
            namespace="ingress-nginx",
            create_namespace=True,
            values={
                "controller": {
                    "replicaCount": replica_count,
                }
            },
        )

        helm_chart.node.add_dependency(custom_resource)
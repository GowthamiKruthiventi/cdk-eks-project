import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_eks_project.cdk_eks_project_stack import CdkEksProjectStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_eks_project/cdk_eks_project_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkEksProjectStack(app, "cdk-eks-project")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

import boto3


def handler(event, context):
    request_type = event.get("RequestType")

    if request_type == "Delete":
        return {"PhysicalResourceId": "helm-values-custom-resource"}

    ssm = boto3.client("ssm")

    response = ssm.get_parameter(Name="/platform/account/env")
    env = response["Parameter"]["Value"]

    if env == "development":
        replica_count = 1
    elif env in ["staging", "production"]:
        replica_count = 2
    else:
        replica_count = 1

    return {
        "PhysicalResourceId": "helm-values-custom-resource",
        "Data": {
            "replicaCount": str(replica_count),
        },
    }
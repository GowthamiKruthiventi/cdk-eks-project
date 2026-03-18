import boto3

def handler(event, context):
    ssm = boto3.client("ssm")

    response = ssm.get_parameter(
        Name="/platform/account/env"
    )

    env = response["Parameter"]["Value"]

    if env == "development":
        replica_count = 1
    elif env in ["staging", "production"]:
        replica_count = 2
    else:
        replica_count = 1

    return {
        "replicaCount": replica_count
    }
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SSM_PARAMETER_NAME = "/platform/account/env"


def handler(event, context):
    request_type = event.get("RequestType")
    physical_id = event.get("PhysicalResourceId", "helm-values-custom-resource")

    logger.info(f"RequestType: {request_type}")

    # On Delete, nothing to do — return the existing PhysicalResourceId
    if request_type == "Delete":
        logger.info("Delete event received — no action required")
        return {"PhysicalResourceId": physical_id}

    try:
        ssm = boto3.client("ssm")
        response = ssm.get_parameter(Name=SSM_PARAMETER_NAME)
        env = response["Parameter"]["Value"].strip().lower()
        logger.info(f"Environment from SSM: {env}")

    except Exception as e:
        logger.error(f"Failed to read SSM parameter '{SSM_PARAMETER_NAME}': {e}")
        raise

    if env == "development":
        replica_count = 1
    elif env in ["staging", "production"]:
        replica_count = 2
    else:
        logger.warning(f"Unrecognised environment '{env}' — defaulting replicaCount to 1")
        replica_count = 1

    logger.info(f"Setting controller.replicaCount to {replica_count}")

    return {
        "PhysicalResourceId": "helm-values-custom-resource",
        "Data": {
            "replicaCount": str(replica_count),
        },
    }
# cdk-eks-project

A Python-based AWS CDK v2 project that provisions an EKS cluster, installs the
ingress-nginx Helm chart, and uses a Lambda-backed Custom Resource to drive Helm
values from an SSM parameter.

---

## Architecture

```
+-------------------------------------------------------------+
|  AWS Account                                                |
|                                                             |
|  +-----------------------------+                            |
|  |  CustomResource             |                            |
|  |                             |                            |
|  |  +----------------------+   |  Get   +------------------+|
|  |  |  Lambda (Python)     |----------->|  SSM:            ||
|  |  |                      |   |        |  /platform/      ||
|  |  +----------+-----------+   |        |  account/env     ||
|  |             | Generates     |        +------------------+|
|  |             v               |                            |
|  |  Attribute: replicaCount    |                            |
|  +-------------+---------------+                            |
|                | References                                 |
|                v                                            |
|  +---------------------+  Deploys into  +-----------------+|
|  |  Helm Chart         |--------------->|  EKS Cluster    ||
|  |  (ingress-nginx)    |                |                 ||
|  +---------------------+                +-----------------+|
+-------------------------------------------------------------+
```

### Resources created

| Resource | Details |
|---|---|
| EKS Cluster | Kubernetes v1.28, 2 x t3.medium nodes, dedicated VPC |
| SSM Parameter | `/platform/account/env` — value: `development` / `staging` / `production` |
| Lambda Function | Python 3.12, reads SSM, returns `replicaCount` as a Custom Resource attribute |
| Custom Resource | `cr.Provider` backed by the Lambda, exposes `replicaCount` attribute |
| Helm Chart | ingress-nginx v4.10.1 in `ingress-nginx` namespace, `controller.replicaCount` driven by the Custom Resource |

### Replica count logic

| SSM value | `controller.replicaCount` |
|---|---|
| `development` | `1` |
| `staging` | `2` |
| `production` | `2` |

---

## Project structure

```
cdk-eks-project/
├── cdk_eks_project/
│   ├── __init__.py
│   └── cdk_eks_project_stack.py   # CDK stack definition
├── lambda/
│   └── index.py                   # Lambda handler (Custom Resource)
├── tests/
│   ├── __init__.py
│   └── unit/
│       ├── __init__.py
│       ├── test_cdk_eks_project_stack.py
│       └── test_index.py          # pytest unit tests for Lambda
├── app.py                         # CDK app entry point
├── cdk.json                       # CDK configuration
├── requirements.txt               # CDK + runtime dependencies
├── requirements-dev.txt           # Dev/test dependencies
└── README.md
```

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| AWS CDK CLI | v2 | `npm install -g aws-cdk` |
| AWS CLI | v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| kubectl | 1.28 | https://kubernetes.io/docs/tasks/tools/ |

### AWS credentials

Make sure your AWS credentials are configured and have sufficient permissions
to create EKS clusters, Lambda functions, SSM parameters, IAM roles, and VPC
resources:

```bash
aws configure
# or
export AWS_PROFILE=your-profile
```

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd cdk-eks-project
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Bootstrap CDK (first time only, per AWS account/region)

```bash
cdk bootstrap
```

---

## Deploy

The target environment is controlled by the CDK context variable `env`.
If not provided it defaults to `development`.

### Development (default)

```bash
cdk deploy
```

### Staging

```bash
cdk deploy -c env=staging
```

### Production

```bash
cdk deploy -c env=production
```

### Confirm changes before deploying

```bash
cdk diff -c env=staging
```

### Synthesise CloudFormation template without deploying

```bash
cdk synth -c env=production
```

---

## Destroy

To tear down all resources:

```bash
cdk destroy
```

> **Note:** The EKS cluster and VPC can take 15-20 minutes to fully delete.

---

## Run unit tests

Install test dependencies:

```bash
pip install pytest boto3
```

Run the Lambda unit tests:

```bash
python -m pytest tests/unit/test_index.py -v
```

Expected output:

```
tests/unit/test_index.py::test_development_returns_replica_count_1 PASSED
tests/unit/test_index.py::test_staging_returns_replica_count_2 PASSED
tests/unit/test_index.py::test_production_returns_replica_count_2 PASSED
tests/unit/test_index.py::test_unknown_env_defaults_to_replica_count_1 PASSED
tests/unit/test_index.py::test_delete_event_does_not_call_ssm PASSED
tests/unit/test_index.py::test_response_contains_physical_resource_id PASSED
tests/unit/test_index.py::test_response_contains_data_key PASSED
tests/unit/test_index.py::test_replica_count_is_string PASSED

8 passed in 0.73s
```

Run all tests including the CDK stack tests:

```bash
python -m pytest tests/ -v
```

---

## Design decisions

**Why `cr.Provider` instead of a raw Custom Resource URL?**
`cr.Provider` manages the full CloudFormation lifecycle (Create / Update / Delete)
automatically and wraps the Lambda correctly so CloudFormation always receives a
valid response — even on failure.

**Why is `replicaCount` returned as a string?**
CloudFormation Custom Resource attributes are always serialised as strings.
The CDK stack uses `Token.as_number()` to re-cast it to a number before passing
it to Helm, which expects an integer for `controller.replicaCount`.

**Why use a CDK context variable for the environment?**
Hardcoding `"development"` would mean the same code could never be used to
deploy staging or production. Using `self.node.try_get_context("env")` keeps
the stack code environment-agnostic and follows 12-factor app principles.

**Why pin the Helm chart version?**
Without a version pin, every `cdk deploy` could silently pull a different chart
version, making deployments non-reproducible. `version="4.10.1"` ensures every
deploy uses the exact same chart regardless of when it runs.

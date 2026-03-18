import index

def test_dev():
    def mock_ssm():
        return {"Parameter": {"Value": "development"}}

    index.boto3.client = lambda x: type("obj", (), {"get_parameter": lambda self, Name: mock_ssm()})()

    result = index.handler({}, {})
    assert result["replicaCount"] == 1


def test_staging():
    def mock_ssm():
        return {"Parameter": {"Value": "staging"}}

    index.boto3.client = lambda x: type("obj", (), {"get_parameter": lambda self, Name: mock_ssm()})()

    result = index.handler({}, {})
    assert result["replicaCount"] == 2


def test_prod():
    def mock_ssm():
        return {"Parameter": {"Value": "production"}}

    index.boto3.client = lambda x: type("obj", (), {"get_parameter": lambda self, Name: mock_ssm()})()

    result = index.handler({}, {})
    assert result["replicaCount"] == 2


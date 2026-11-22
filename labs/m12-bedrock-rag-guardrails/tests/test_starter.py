"""The starter imports cleanly, keeps the request validation, and marks the work to do."""

import json

from botocore.stub import Stubber

from conftest import STARTER


def test_starter_lambda_imports_and_validates_requests(load_app):
    app = load_app(STARTER)
    with Stubber(app.kb), Stubber(app.bedrock):
        assert app.handler({"body": "{}"}, None)["statusCode"] == 400
        result = app.handler({"body": json.dumps({"question": "Combien de jours ?"})}, None)
    assert result["statusCode"] == 501


def test_starter_has_todo_markers_for_each_step_to_write():
    expected = {
        "terraform/s3.tf": "TODO (step 1)",
        "terraform/knowledge_base.tf": "TODO (step 2)",
        "terraform/guardrail.tf": "TODO (step 5)",
        "terraform/lambda.tf": "TODO (step 6)",
        "lambda/app.py": "TODO (step 6)",
        "terraform/api.tf": "TODO (step 7)",
    }
    for path, marker in expected.items():
        assert marker in (STARTER / path).read_text(encoding="utf-8"), path

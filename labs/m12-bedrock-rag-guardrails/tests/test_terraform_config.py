"""Static checks of the Terraform code: the names, settings and permissions the lesson relies on.
`terraform validate` (run by test.sh) checks the syntax and the provider schema; these tests
check the values."""

import pytest

from conftest import SOLUTION
from tfconfig import TerraformConfig


@pytest.fixture(scope="module")
def tf():
    return TerraformConfig(SOLUTION / "terraform")


def test_providers_are_pinned_exactly(tf):
    providers = tf.required_providers()
    assert providers["aws"] == {"source": "hashicorp/aws", "version": "6.73.0"}
    assert providers["archive"] == {"source": "hashicorp/archive", "version": "2.8.1"}


def test_defaults_match_the_lesson(tf):
    assert tf.default("region") == "eu-west-3"
    assert tf.default("model_id") == "eu.anthropic.claude-opus-5-5"
    assert tf.default("embedding_model_id") == "amazon.titan-embed-text-v2:0"
    assert tf.default("embedding_dimensions") == 1024
    assert tf.default("lab_name") == "lab-rag-rh"
    assert tf.default("knowledge_base_name") == "kb-lab-rh"


def test_every_resource_is_tagged_for_the_lab(tf):
    tags = tf.providers["aws"]["default_tags"][0]["tags"]
    assert tags["Lab"] == "m12-bedrock-rag-guardrails"


def test_bucket_name_and_documents(tf):
    assert tf.locals["bucket"] == "${var.lab_name}-${local.account_id}"
    assert tf.resource("aws_s3_bucket", "docs")["force_destroy"] is True
    assert tf.resource("aws_s3_object", "docs")["key"] == "docs/${each.value}"


def test_vector_store_and_knowledge_base(tf):
    collection = tf.resource("aws_opensearchserverless_collection", "kb")
    assert collection["type"] == "VECTORSEARCH"
    kb = tf.resource("aws_bedrockagent_knowledge_base", "this")
    assert kb["name"] == "${var.knowledge_base_name}"
    storage = kb["storage_configuration"][0]
    assert storage["type"] == "OPENSEARCH_SERVERLESS"
    mapping = storage["opensearch_serverless_configuration"][0]["field_mapping"][0]
    assert mapping == {
        "vector_field": "${local.vector_field}",
        "text_field": "${local.text_field}",
        "metadata_field": "${local.metadata_field}",
    }
    assert tf.locals["vector_field"] == "bedrock-knowledge-base-default-vector"
    assert tf.locals["text_field"] == "AMAZON_BEDROCK_TEXT_CHUNK"
    assert tf.locals["metadata_field"] == "AMAZON_BEDROCK_METADATA"
    # Metadata filtering (step 4) needs the faiss engine.
    properties = tf.locals["index_body"]["mappings"]["properties"]
    assert set(properties) == {"${(local.vector_field)}", "${(local.text_field)}", "${(local.metadata_field)}"}
    vector = properties["${(local.vector_field)}"]
    assert vector["method"]["engine"] == "faiss"
    assert vector["dimension"] == "${var.embedding_dimensions}"


def test_guardrail_matches_the_lesson(tf):
    guardrail = tf.resource("aws_bedrock_guardrail", "this")
    assert guardrail["name"] == "${var.lab_name}"
    assert guardrail["blocked_input_messaging"] == (
        "Je ne peux pas traiter cette demande. Pour une situation personnelle, contactez directement le service RH."
    )
    assert guardrail["blocked_outputs_messaging"] == (
        "Je ne trouve pas de réponse fiable dans les documents disponibles. Contactez le service RH."
    )
    assert tf.locals["content_filters"] == {
        "HATE": {"input": "HIGH", "output": "HIGH"},
        "INSULTS": {"input": "HIGH", "output": "HIGH"},
        "SEXUAL": {"input": "HIGH", "output": "HIGH"},
        "VIOLENCE": {"input": "HIGH", "output": "HIGH"},
        "MISCONDUCT": {"input": "HIGH", "output": "HIGH"},
        "PROMPT_ATTACK": {"input": "HIGH", "output": "NONE"},
    }
    topic = guardrail["topic_policy_config"][0]["topics_config"][0]
    assert topic["name"] == "Conseil juridique individuel"
    assert topic["type"] == "DENY"
    assert len(topic["examples"]) == 2
    pii = {e["type"]: e for e in guardrail["sensitive_information_policy_config"][0]["pii_entities_config"]}
    assert pii["EMAIL"] == {"type": "EMAIL", "action": "ANONYMIZE", "input_enabled": False}
    assert pii["PHONE"] == {"type": "PHONE", "action": "ANONYMIZE", "input_enabled": False}
    assert pii["INTERNATIONAL_BANK_ACCOUNT_NUMBER"]["action"] == "BLOCK"
    grounding = guardrail["contextual_grounding_policy_config"][0]["filters_config"]
    assert {f["type"]: f["threshold"] for f in grounding} == {"GROUNDING": 0.5, "RELEVANCE": 0.5}
    assert tf.resource("aws_bedrock_guardrail_version", "v1")["description"] == "Version 1 du lab"


def test_function_matches_the_lesson(tf):
    function = tf.resource("aws_lambda_function", "rag")
    assert function["function_name"] == "${var.lab_name}"
    assert function["runtime"] == "python3.12"
    assert function["handler"] == "app.handler"
    assert function["timeout"] == 30
    assert function["memory_size"] == 512
    assert set(function["environment"][0]["variables"]) == {"KB_ID", "GUARDRAIL_ID", "GUARDRAIL_VERSION", "MODEL_ID", "MODEL_EFFORT"}
    assert tf.resource("aws_iam_role", "lambda")["name"] == "${var.lab_name}-lambda"
    assert tf.resource("aws_iam_role_policy", "bedrock_rag")["name"] == "bedrock-rag"


def test_function_role_is_least_privilege(tf):
    statements = {s["sid"]: s for s in tf.data["aws_iam_policy_document"]["bedrock_rag"]["statement"]}
    assert set(statements) == {"Retrieve", "InferenceProfile", "DestinationModels", "Guardrail"}
    assert statements["Retrieve"]["actions"] == ["bedrock:Retrieve"]
    assert statements["Retrieve"]["resources"] == ["${aws_bedrockagent_knowledge_base.this.arn}"]
    assert statements["DestinationModels"]["condition"][0]["variable"] == "bedrock:InferenceProfileArn"
    assert statements["Guardrail"]["resources"] == ["${aws_bedrock_guardrail.this.guardrail_arn}"]
    for document in tf.data["aws_iam_policy_document"].values():
        for statement in document.get("statement", []):
            assert "*" not in statement.get("resources", []), statement
            assert not any(action.endswith(":*") for action in statement.get("actions", [])), statement


def test_api_is_a_quick_create_http_api(tf):
    api = tf.resource("aws_apigatewayv2_api", "rag")
    assert api["name"] == "${var.lab_name}"
    assert api["protocol_type"] == "HTTP"
    assert api["target"] == "${aws_lambda_function.rag.arn}"
    permission = tf.resource("aws_lambda_permission", "apigw")
    assert permission["statement_id"] == "apigw-lab"
    assert permission["principal"] == "apigateway.amazonaws.com"

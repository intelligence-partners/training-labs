"""Unit tests of src/app.py, with DynamoDB mocked by moto (no AWS account needed)."""

import base64
import json
import logging
import re

PROMPT_TEXT = "Résume le contrat ci-dessous en cinq points, en citant les articles."


def http_event(route_key, body=None, path_parameters=None, base64_body=False):
    """A minimal API Gateway HTTP API event, payload format 2.0."""
    method, path = route_key.split(" ", 1)
    event = {
        "version": "2.0",
        "routeKey": route_key,
        "rawPath": path,
        "requestContext": {"http": {"method": method, "path": path}},
        "isBase64Encoded": base64_body,
    }
    if body is not None:
        raw = body if isinstance(body, str) else json.dumps(body)
        event["body"] = base64.b64encode(raw.encode("utf-8")).decode() if base64_body else raw
    if path_parameters is not None:
        event["pathParameters"] = path_parameters
    return event


def call(app, event):
    result = app.handler(event, None)
    assert result["headers"] == {"Content-Type": "application/json"}
    return result["statusCode"], json.loads(result["body"])


def create(app, name="resume-contrat", text=PROMPT_TEXT):
    return call(app, http_event("POST /prompts", {"nom": name, "texte": text}))


def test_post_creates_the_prompt_and_returns_201(app, table):
    status, body = create(app)

    assert status == 201
    assert re.fullmatch(r"[0-9a-f]{32}", body["id"])
    assert body["nom"] == "resume-contrat"
    assert body["texte"] == PROMPT_TEXT
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+00:00$", body["creeLe"])
    assert table.get_item(Key={"id": body["id"]})["Item"] == body


def test_response_keeps_accents_unescaped(app):
    result = app.handler(http_event("POST /prompts", {"nom": "resume-contrat", "texte": PROMPT_TEXT}), None)
    assert "Résume" in result["body"]


def test_get_returns_the_same_object(app):
    _, created = create(app)

    status, body = call(app, http_event("GET /prompts/{id}", path_parameters={"id": created["id"]}))

    assert status == 200
    assert body == created


def test_get_unknown_id_returns_404(app):
    status, body = call(app, http_event("GET /prompts/{id}", path_parameters={"id": "0" * 32}))
    assert status == 404
    assert body == {"erreur": "prompt introuvable"}


def test_missing_text_returns_the_lesson_error(app):
    status, body = call(app, http_event("POST /prompts", {"nom": "sans-texte"}))
    assert status == 400
    assert body == {"erreur": "texte obligatoire, 10 000 caractères au plus"}


def test_missing_name_is_rejected(app):
    status, body = call(app, http_event("POST /prompts", {"texte": PROMPT_TEXT}))
    assert status == 400
    assert body == {"erreur": "nom obligatoire, 100 caractères au plus"}


def test_length_limits(app):
    assert create(app, name="n" * 100)[0] == 201
    assert create(app, name="n" * 101)[0] == 400
    assert create(app, text="t" * 10_000)[0] == 201
    assert create(app, text="t" * 10_001)[0] == 400
    assert create(app, name="   ")[0] == 400


def test_invalid_json_returns_400(app):
    status, body = call(app, http_event("POST /prompts", "{not json"))
    assert status == 400
    assert body == {"erreur": "corps JSON invalide"}


def test_json_that_is_not_an_object_returns_400(app):
    status, body = call(app, http_event("POST /prompts", '["nom", "texte"]'))
    assert status == 400
    assert body == {"erreur": "un objet JSON est attendu"}


def test_empty_body_is_rejected(app):
    status, _ = call(app, http_event("POST /prompts"))
    assert status == 400


def test_base64_encoded_body_is_decoded(app):
    event = http_event("POST /prompts", {"nom": "resume-contrat", "texte": PROMPT_TEXT}, base64_body=True)
    status, body = call(app, event)
    assert status == 201
    assert body["texte"] == PROMPT_TEXT


def test_unknown_route_returns_404(app):
    status, body = call(app, http_event("GET /prompts"))
    assert status == 404
    assert body == {"erreur": "route inconnue"}


def test_log_line_has_id_and_size_but_never_the_text(app, caplog):
    with caplog.at_level(logging.INFO):
        _, body = create(app)

    messages = [record.getMessage() for record in caplog.records]
    assert f"prompt_cree id={body['id']} taille={len(PROMPT_TEXT)}" in messages
    assert all(PROMPT_TEXT not in message for message in messages)


def test_function_only_calls_putitem_and_getitem(app):
    """The code needs exactly the two actions that the execution role allows."""
    operations = []

    def record(model, **kwargs):
        operations.append(model.name)

    app.table.meta.client.meta.events.register("before-call.dynamodb", record)
    _, created = create(app)
    call(app, http_event("GET /prompts/{id}", path_parameters={"id": created["id"]}))
    call(app, http_event("GET /prompts/{id}", path_parameters={"id": "f" * 32}))

    assert set(operations) == {"PutItem", "GetItem"}

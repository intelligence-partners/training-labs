"""Step 2 and step 3: the server's primitives, through the in-memory MCP client.

The in-memory Client speaks the real MCP protocol to the server object, without a
subprocess: the fastest way to test every tool, resource and prompt.
"""

import json
from datetime import date

import pytest

from mcp import Client, MCPError

import server
from strings import S

pytestmark = pytest.mark.anyio


async def test_lists_two_tools_with_schemas_and_annotations(crm_file):
    async with Client(server.mcp) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}

    assert set(tools) == {"crm_search_clients", "crm_add_note"}
    search = tools["crm_search_clients"]
    assert search.annotations.read_only_hint is True
    assert search.annotations.open_world_hint is False
    props = search.input_schema["properties"]
    assert props["limit"]["maximum"] == 20 and props["limit"]["minimum"] == 1
    assert props["limit"]["default"] == 5
    assert search.input_schema["required"] == ["query"]
    secteurs = next(s for s in props["secteur"]["anyOf"] if "enum" in s)["enum"]
    assert secteurs == ["industrie", "assurance", "logistique", "sante", "finance", "agroalimentaire"]
    assert search.output_schema["properties"]["result"]["type"] == "array"
    add = tools["crm_add_note"]
    assert add.annotations.read_only_hint is False
    assert add.annotations.destructive_hint is False
    assert add.annotations.idempotent_hint is False
    assert set(add.input_schema["required"]) == {"client_id", "texte", "auteur"}


async def test_search_lyon(crm_file):
    async with Client(server.mcp) as client:
        result = await client.call_tool("crm_search_clients", {"query": "lyon"})

    assert result.is_error is False
    ids = [json.loads(block.text)["id"] for block in result.content]
    assert ids == ["C-1001", "C-1004"]  # one text block per client, for the model
    assert result.structured_content == {"result": [  # and structured content, for the application
        {"id": "C-1001", "nom": "Aciéries du Rhône", "ville": "Lyon", "secteur": "industrie", "statut": "client"},
        {"id": "C-1004", "nom": "Clinique du Parc", "ville": "Lyon", "secteur": "sante", "statut": "prospect"},
    ]}


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"query": ""}, ["C-1001", "C-1002", "C-1003", "C-1004", "C-1005"]),  # default limit 5
        ({"query": "", "limit": 20}, ["C-1001", "C-1002", "C-1003", "C-1004", "C-1005", "C-1006"]),
        ({"query": "LYON", "secteur": "sante"}, ["C-1004"]),
        ({"query": S["contact_query"]}, ["C-1002"]),  # the contact person is searched too
        ({"query": "", "secteur": "finance"}, ["C-1005"]),
        ({"query": "Marseille"}, []),
    ],
)
async def test_search_filters(crm_file, arguments, expected):
    async with Client(server.mcp) as client:
        result = await client.call_tool("crm_search_clients", arguments)
    assert [c["id"] for c in result.structured_content["result"]] == expected


async def test_limit_out_of_bounds_is_a_tool_error(crm_file):
    async with Client(server.mcp) as client:
        result = await client.call_tool("crm_search_clients", {"query": "", "limit": 99})

    assert result.is_error is True
    assert "less than or equal to 20" in result.content[0].text
    assert "Traceback" not in result.content[0].text


async def test_unknown_sector_is_rejected(crm_file):
    async with Client(server.mcp) as client:
        result = await client.call_tool("crm_search_clients", {"query": "", "secteur": "spatial"})
    assert result.is_error is True


async def test_add_note_writes_today(crm_file):
    async with Client(server.mcp) as client:
        result = await client.call_tool(
            "crm_add_note", {"client_id": "C-1002", "texte": "Rappel prévu jeudi à 10 h.", "auteur": "Léa"})

    assert result.is_error is False
    assert result.structured_content == {
        "result": S["note_added"]}
    saved = json.loads(crm_file.read_text(encoding="utf-8"))
    fiche = next(c for c in saved["clients"] if c["id"] == "C-1002")
    assert fiche["notes"] == [{"date": date.today().isoformat(), "auteur": "Léa", "texte": "Rappel prévu jeudi à 10 h."}]
    assert "Mutuelle Atlantique" in crm_file.read_text(encoding="utf-8")  # ensure_ascii=False keeps accents readable


async def test_add_note_unknown_client_tells_how_to_fix(crm_file):
    async with Client(server.mcp) as client:
        result = await client.call_tool("crm_add_note", {"client_id": "C-9999", "texte": "x", "auteur": "Léa"})

    assert result.is_error is True
    assert S["unknown_client"] in result.content[0].text
    from conftest import DATA

    assert json.loads(crm_file.read_text(encoding="utf-8")) == json.loads(DATA.read_text(encoding="utf-8"))


async def test_resource_template_and_read(crm_file):
    async with Client(server.mcp) as client:
        templates = (await client.list_resource_templates()).resource_templates
        fiche = await client.read_resource("crm://clients/C-1003")

    assert [(t.uri_template, t.mime_type) for t in templates] == [("crm://clients/{client_id}", "application/json")]
    content = fiche.contents[0]
    assert content.mime_type == "application/json"
    data = json.loads(content.text)
    assert data["nom"] == "Transports Vercors"
    assert data["notes"][0]["auteur"] == "Nadia"


async def test_missing_record_is_resource_not_found(crm_file):
    async with Client(server.mcp) as client:
        with pytest.raises(MCPError, match=S["missing_record"]):
            await client.read_resource("crm://clients/C-9999")


async def test_prompt(crm_file):
    async with Client(server.mcp) as client:
        prompts = (await client.list_prompts()).prompts
        prompt = await client.get_prompt("preparer_rendez_vous", {"client_id": "C-1003"})

    (listed,) = prompts
    assert listed.title == S["prompt_title"]
    assert [(a.name, a.required) for a in listed.arguments] == [("client_id", True)]
    assert prompt.messages[0].content.text.startswith(S["prompt_start"])


async def test_instructions(crm_file):
    async with Client(server.mcp) as client:
        assert client.instructions.startswith(S["instructions_start"])
        assert client.server_info.name == "orbis-crm"


def test_data_path_is_absolute_by_default():
    # Computed from the file, so the server finds its data whatever the working directory.
    assert server.DATA_FILE.is_absolute()
    assert server.DATA_FILE == server.Path(server.__file__).parent / "crm_data.json"

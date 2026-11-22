"""The SigV4 MCP client of the Gateway, without any network call."""

import httpx
import pytest
from strands.tools.mcp import MCPClient

GATEWAY_URL = "https://supportlab-tools-abcdefghij.gateway.bedrock-agentcore.eu-west-3.amazonaws.com/mcp"


def test_no_gateway_url_means_no_tools(load_agent):
    gateway_client = load_agent("gateway_client")
    assert gateway_client.get_gateway_client() is None


def test_gateway_url_gives_an_mcp_client(load_agent):
    gateway_client = load_agent("gateway_client", AGENTCORE_GATEWAY_TOOLS_URL=GATEWAY_URL)
    assert isinstance(gateway_client.get_gateway_client(), MCPClient)


@pytest.mark.parametrize(
    "url, expected",
    [
        (GATEWAY_URL, GATEWAY_URL),
        (GATEWAY_URL + "/", GATEWAY_URL),
        (GATEWAY_URL.removesuffix("/mcp"), GATEWAY_URL),
        (GATEWAY_URL.removesuffix("/mcp") + "/", GATEWAY_URL),
    ],
)
def test_mcp_endpoint_always_ends_with_mcp(load_agent, url, expected):
    gateway_client = load_agent("gateway_client")
    assert gateway_client.mcp_url(url) == expected


def test_requests_are_signed_for_bedrock_agentcore(load_agent):
    gateway_client = load_agent("gateway_client")
    body = b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
    request = httpx.Request("POST", GATEWAY_URL, content=body, headers={"content-type": "application/json"})

    flow = gateway_client.GatewayAuth("eu-west-3").auth_flow(request)
    signed = next(flow)

    authorization = signed.headers["authorization"]
    assert authorization.startswith("AWS4-HMAC-SHA256 Credential=testing/")
    assert "/eu-west-3/bedrock-agentcore/aws4_request" in authorization
    assert "host" in authorization.split("SignedHeaders=")[1]
    assert signed.headers["x-amz-security-token"] == "testing"
    assert "x-amz-date" in signed.headers
    assert signed.content == body

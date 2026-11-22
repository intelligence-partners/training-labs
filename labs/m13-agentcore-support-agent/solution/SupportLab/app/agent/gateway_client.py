"""MCP client that signs every request to the Gateway with the runtime's AWS credentials (SigV4).

Adapted from the official AWS tutorial. The deployment provides the Gateway address in
AGENTCORE_GATEWAY_TOOLS_URL (the name the AgentCore CLI uses for a Gateway called "tools").
"""

import os

import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_TOOLS_URL")
REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
MCP_PATH = "/mcp"


class GatewayAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, region: str):
        self._credentials = Session().get_credentials()
        self._region = region

    def auth_flow(self, request: httpx.Request):
        signed = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers={"host": request.url.host, "content-type": request.headers.get("content-type", "")},
        )
        SigV4Auth(self._credentials.get_frozen_credentials(), "bedrock-agentcore", self._region).add_auth(signed)
        request.headers.update(dict(signed.headers))
        yield request


def mcp_url(gateway_url: str) -> str:
    """The MCP endpoint of a Gateway is its URL ending with /mcp."""
    url = gateway_url.rstrip("/")
    return url if url.endswith(MCP_PATH) else url + MCP_PATH


def get_gateway_client() -> MCPClient | None:
    if not GATEWAY_URL:
        return None
    url = mcp_url(GATEWAY_URL)
    return MCPClient(lambda: streamablehttp_client(url, auth=GatewayAuth(REGION)))

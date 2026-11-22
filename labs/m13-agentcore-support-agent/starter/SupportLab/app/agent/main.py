import os
import re

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from gateway_client import get_gateway_client
from memory.session import get_memory_session_manager

app = BedrockAgentCoreApp()
log = app.logger

# TODO (step 5): the system prompt of the Acme support agent (see the lesson): answer in French
# in five sentences at most, always read the order with the tool, convert refunds to cents and
# confirm them, and offer a ticket when a tool refuses an action.
SYSTEM_PROMPT = """TODO"""

# AgentCore is model-agnostic: any model or inference profile enabled in the account works,
# and BedrockModel can be swapped for another Strands model provider.
MODEL_ID = os.getenv("MODEL_ID", "eu.anthropic.claude-opus-5-5")
MODEL = BedrockModel(model_id=MODEL_ID)
GATEWAY = get_gateway_client()
ACTOR_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
_agents: dict[tuple[str, str], Agent] = {}


def _agent_for(session_id: str, actor_id: str) -> Agent:
    # TODO (step 5): keep one Agent per (session_id, actor_id), built with MODEL, SYSTEM_PROMPT,
    # the Gateway tools (tools=[GATEWAY] if GATEWAY else []) and the memory session manager
    # get_memory_session_manager(session_id, actor_id).
    raise NotImplementedError("TODO (step 5)")


@app.entrypoint
def invoke(payload, context):
    # TODO (step 5): validate "prompt" (non-empty string) and "actorId" (ACTOR_RE), and return
    # {"error": "..."} when they are invalid.
    # TODO (step 5): call _agent_for(context.session_id or "local-dev-session-000000000000000000",
    # actor_id) with the prompt, and return {"result": <the text blocks of result.message>}.
    return {"error": "TODO (step 5): the agent is not written yet."}


if __name__ == "__main__":
    app.run()

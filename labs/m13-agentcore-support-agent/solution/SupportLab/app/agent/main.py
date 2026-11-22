import os
import re

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from gateway_client import get_gateway_client
from memory.session import get_memory_session_manager

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT = """Tu es l'agent de support d'Acme, un site de vente en ligne.
- Réponds en français, en cinq phrases au plus.
- Lis toujours la commande avec l'outil avant d'en parler ; n'invente jamais un statut ni un montant.
- Pour un remboursement, convertis le montant en centimes et confirme-le avant d'appeler l'outil.
- Si un outil refuse une action, explique-le simplement et propose d'ouvrir un ticket."""

# AgentCore is model-agnostic: any model or inference profile enabled in the account works,
# and BedrockModel can be swapped for another Strands model provider.
MODEL_ID = os.getenv("MODEL_ID", "eu.anthropic.claude-opus-5-5")
MODEL = BedrockModel(model_id=MODEL_ID)
GATEWAY = get_gateway_client()
ACTOR_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")
_agents: dict[tuple[str, str], Agent] = {}


def _agent_for(session_id: str, actor_id: str) -> Agent:
    key = (session_id, actor_id)
    if key not in _agents:
        _agents[key] = Agent(
            model=MODEL,
            system_prompt=SYSTEM_PROMPT,
            tools=[GATEWAY] if GATEWAY else [],
            session_manager=get_memory_session_manager(session_id, actor_id),
        )
    return _agents[key]


@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt")
    actor_id = payload.get("actorId", "")
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "Le champ 'prompt' doit être une chaîne non vide."}
    if not isinstance(actor_id, str) or not ACTOR_RE.match(actor_id):
        return {"error": "Le champ 'actorId' est obligatoire : lettres, chiffres, tiret ou tiret bas."}
    session_id = context.session_id or "local-dev-session-000000000000000000"
    log.info("Invocation pour l'acteur %s", actor_id)
    result = _agent_for(session_id, actor_id)(prompt)
    text = "".join(block.get("text", "") for block in result.message["content"])
    return {"result": text}


if __name__ == "__main__":
    app.run()

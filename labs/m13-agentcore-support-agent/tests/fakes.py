"""A scripted Strands model and local stand-ins for the three Gateway tools."""

import json

from strands import tool
from strands.models.model import Model
from strands.tools import ToolProvider


class FakeModel(Model):
    """Plays a list of turns. A turn is {"text": "..."} or {"tool": (name, input)}."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls.append(
            {
                "messages": json.loads(json.dumps(messages, default=str)),
                "tools": sorted(spec["name"] for spec in (tool_specs or [])),
                "system_prompt": system_prompt,
            }
        )
        turn = self.turns.pop(0)
        yield {"messageStart": {"role": "assistant"}}
        if "tool" in turn:
            name, tool_input = turn["tool"]
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"tooluse-{len(self.calls)}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(tool_input)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": turn["text"]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}, "metrics": {"latencyMs": 1}}}


class FakeGateway(ToolProvider):
    """Serves support___getOrder, support___createTicket and support___createRefund.

    Refunds above 5000 cents are refused the way the Gateway refuses a call denied by Policy:
    the tool fails, and the agent receives an error tool result."""

    def __init__(self):
        self.calls = []
        gateway = self

        @tool(name="support___getOrder")
        def get_order(orderId: str) -> dict:
            """Return the status, carrier and total in cents of an order."""
            gateway.calls.append(("getOrder", {"orderId": orderId}))
            return {"orderId": orderId, "status": "expédiée", "carrier": "Colissimo", "totalCents": 18990}

        @tool(name="support___createTicket")
        def create_ticket(orderId: str, summary: str) -> dict:
            """Open a ticket for the human support team."""
            gateway.calls.append(("createTicket", {"orderId": orderId, "summary": summary}))
            return {"ticketId": "T-" + orderId, "status": "ouvert", "summary": summary}

        @tool(name="support___createRefund")
        def create_refund(orderId: str, amountCents: int, reason: str) -> dict:
            """Refund all or part of an order, in euro cents."""
            gateway.calls.append(("createRefund", {"orderId": orderId, "amountCents": amountCents, "reason": reason}))
            if amountCents > 5000 or orderId.startswith("B2B-"):
                raise PermissionError("Tool Execution Denied: No policy applies to the request (denied by default).")
            return {"refundId": "R-" + orderId, "amountCents": amountCents, "status": "accepté"}

        self._tools = [get_order, create_ticket, create_refund]

    async def load_tools(self, **kwargs):
        return self._tools

    def add_consumer(self, consumer_id, **kwargs):
        pass

    def remove_consumer(self, consumer_id, **kwargs):
        pass

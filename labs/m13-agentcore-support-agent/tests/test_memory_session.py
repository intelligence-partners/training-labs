"""Memory per actor: the retrieval namespaces match the strategies Terraform creates."""

import re

import pytest

from conftest import SOLUTION
from tfconfig import TerraformConfig


class Recorder:
    def __init__(self, config, region):
        self.config = config
        self.region = region


def test_no_memory_id_means_no_session_manager(load_agent):
    session = load_agent("memory.session")
    assert session.get_memory_session_manager("s" * 40, "c-4821") is None


@pytest.fixture
def manager(load_agent, monkeypatch):
    session = load_agent("memory.session", MEMORY_AGENTMEMORY_ID="supportlab_agentMemory-AbCdEf1234")
    monkeypatch.setattr(session, "AgentCoreMemorySessionManager", Recorder)
    return session.get_memory_session_manager("support-lab-session-0003-abcdefghijk", "c-4821")


def test_session_manager_is_scoped_to_the_actor(manager):
    assert manager.region == "eu-west-3"
    assert manager.config.memory_id == "supportlab_agentMemory-AbCdEf1234"
    assert manager.config.actor_id == "c-4821"
    assert manager.config.session_id == "support-lab-session-0003-abcdefghijk"
    assert all("c-4821" in namespace for namespace in manager.config.retrieval_config)


def test_relevance_threshold_is_lowered_to_0_3(manager):
    assert {k: (v.top_k, v.relevance_score) for k, v in manager.config.retrieval_config.items()} == {
        "/users/c-4821/facts": (3, 0.3),
        "/users/c-4821/preferences": (3, 0.3),
        "/episodes/c-4821/support-lab-session-0003-abcdefghijk": (5, 0.3),
        "/summaries/c-4821": (3, 0.3),
    }


def test_every_retrieved_namespace_is_filled_by_a_strategy(manager):
    tf = TerraformConfig(SOLUTION / "terraform" / "support-agent")
    templates = [s["namespace_templates"][0] for s in tf.resources["aws_bedrockagentcore_memory_strategy"].values()]
    patterns = [re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", t) + "(/.*)?$") for t in templates]
    prefixes = [re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", t.rsplit("/", 1)[0]) + "$") for t in templates]
    for namespace in manager.config.retrieval_config:
        assert any(p.match(namespace) for p in patterns + prefixes), namespace

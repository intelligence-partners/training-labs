"""The lesson's commands, run as written, in a fresh project folder.

Local models are the deterministic fakes (tests/fakes on PYTHONPATH) and Claude is the local
fake API (ANTHROPIC_BASE_URL); Chroma and rank_bm25 are real. The assertions check the
lesson's exact output lines wherever the output does not depend on the real models.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import LAB, TARGET, subprocess_env

CDD = "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
SPORT = "L'entreprise rembourse-t-elle les abonnements de salle de sport ?"


@pytest.fixture
def project(tmp_path):
    for source in TARGET.glob("*.py"):
        shutil.copy(source, tmp_path / source.name)
    shutil.copytree(TARGET / "corpus", tmp_path / "corpus")
    return tmp_path


@pytest.fixture
def sh(project, fake_api):
    python_dir = str(Path(sys.executable).parent)

    def run(command: str, **env: str) -> subprocess.CompletedProcess:
        full_env = subprocess_env(ANTHROPIC_BASE_URL=fake_api.url, ANTHROPIC_API_KEY="sk-ant-test",
                                  PATH=python_dir + os.pathsep + os.environ["PATH"], **env)
        result = subprocess.run(["bash", "-c", command], cwd=project, env=full_env, capture_output=True,
                                text=True, timeout=300)
        assert result.returncode == 0, f"{command}\n{result.stdout}\n{result.stderr}"
        return result

    return run


def test_steps_3_to_7(sh, project):
    assert sh("python ingestion.py").stdout.strip() == "18 chunks écrits dans chunks.jsonl, issus de 7 fichiers"
    assert sh("python index.py").stdout.strip() == "18 vecteurs de 384 dimensions indexés dans ./index"

    prc = sh('python recherche.py "Que dit la PRC-114 avant un redémarrage ?"').stdout.splitlines()
    assert prc[0] == ("1. procedure-prc-114.md#0               Préalables               "
                      "Avant tout redémarrage, obtenez l'accord du responsable d'ex…")
    salarie = sh('python recherche.py "Quelle est l\'enveloppe d\'augmentations collectives 2026 ?"').stdout
    rh = sh('python recherche.py "Quelle est l\'enveloppe d\'augmentations collectives 2026 ?" --profil rh').stdout
    assert "remunerations-2026.md" not in salarie
    assert rh.splitlines()[0].startswith("1. remunerations-2026.md#0")

    cited = sh(f'python assistant.py "{CDD}"').stdout
    assert cited == (
        "Oui. En CDD de plus de six mois, le télétravail est possible avec l'accord écrit de votre manager[1], "
        "jusqu'à trois jours par semaine[2].\n"
        "\n"
        "Sources :\n"
        "[1] Politique de télétravail — Éligibilité (kb://politique-teletravail.md#0)\n"
        "[2] Politique de télétravail — Rythme (kb://politique-teletravail.md#1)\n"
        "\n"
        "[claude-opus-5-5 · entrée 1450 · sortie 210 · 0.0100 $]\n"
    )
    abstention = sh(f'python assistant.py "{SPORT}"').stdout
    assert abstention == (
        "« Je ne trouve pas cette information dans la documentation disponible. »\n"
        "\n"
        "[claude-opus-5-5 · entrée 1190 · sortie 95 · 0.0067 $]\n"
    )
    assert "archives/" not in cited


def test_steps_8_and_9(sh):
    sh("python ingestion.py && python index.py")

    retrieval = sh("python evaluation.py").stdout.splitlines()
    generation = sh("python evaluation.py --generation").stdout.splitlines()
    variants = [sh(f"python evaluation.py {flag}").stdout.splitlines()[-1] for flag in ("--sans-rerank", "--sans-hybride")]
    with_context = sh("python contextualiser.py && python index.py && python evaluation.py").stdout.splitlines()

    assert re.fullmatch(r"Rappel@5 : \d\.\d\d   MRR : \d\.\d\d", retrieval[-1])
    assert re.fullmatch(r"Génération correcte : \d+/11", generation[-1])
    assert all(v.startswith("Rappel@5 : ") for v in variants)
    assert with_context[0] == "18 chunks contextualisés, 0 tokens lus depuis le cache, coût estimé 0.0005 $"
    assert with_context[1] == "18 vecteurs de 384 dimensions indexés dans ./index"
    assert with_context[-1].startswith("Rappel@5 : ")


def test_cleanup_removes_generated_files(sh, project, tmp_path):
    sh("python ingestion.py && python index.py")
    hf_home = tmp_path / "hf"
    for name in ("models--intfloat--multilingual-e5-small", "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1",
                 "models--someone--else"):
        (hf_home / "hub" / name).mkdir(parents=True)

    result = sh(f'bash "{LAB / "cleanup.sh"}" "{project}"', HF_HOME=str(hf_home))

    assert not (project / "index").exists()
    assert not (project / "chunks.jsonl").exists()
    assert (project / "corpus").exists()  # the corpus and the code are kept
    assert sorted(p.name for p in (hf_home / "hub").iterdir()) == ["models--someone--else"]
    assert "removed" in result.stdout

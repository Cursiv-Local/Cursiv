"""U99: operational self-knowledge. Cursiv knows what it supports, what is on, and what
it actually checked -- and corrects itself instead of defending a wrong answer.

The fixtures are the real failures from the U98 conversation (see the docstrings).
Everything here is application-owned and model-free; how the local model writes is
measured separately by scripts/self_knowledge_live.py against the real model.
"""
from pathlib import Path

import pytest

from cursiv_engine.core import capabilities, claim_evidence, evidence_log, native_answers

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def fresh_log():
    evidence_log.clear()
    yield
    evidence_log.clear()


def test_every_capability_names_real_code_and_tests():
    for c in capabilities.CAPABILITIES:
        for p in c.code + c.tests:
            assert (ROOT / p).exists(), f"{c.key}: {p} doesn't exist"


def test_a_failed_state_read_is_unknown_never_off():
    def broken():
        raise OSError("settings unreadable")
    reader = capabilities._read(broken)
    assert reader().startswith("unknown")


# Test B -- "Does Cursiv have an update mechanism?" (it said: "no update mechanism")
def test_b_updater_is_described_accurately():
    text = native_answers.answer("Does Cursiv have an update mechanism?")
    assert text and "Updates" in text and "GitHub" in text and "owner-signed" in text
    assert "only when you click" in text and "off by default" in text and "never changes its own code" in text
    assert "no AI model" in text


# Test C -- "Does Cursiv support online AI?" even with offline mode on
def test_c_online_ai_is_optional_not_missing(monkeypatch):
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, "is_offline", lambda: True)
    text = native_answers.answer("Does Cursiv support online AI?")
    assert "Optional online AI providers" in text and "OpenAI" in text and "never in offline mode" in text


# Test D -- "Does Cursiv have external dependencies?" (it said: "no external dependencies")
def test_d_dependencies_include_ollama_without_requiring_the_cloud():
    text = native_answers.answer("Does Cursiv have external dependencies?")
    assert "Ollama" in text and "PyQt6" in text and "everyday local use doesn't" in text


# Test E -- "Are you using the internet right now?"
def test_e_current_internet_state_comes_from_settings(monkeypatch):
    from cursiv_engine.core import netgate
    from cursiv_engine.chat import status
    monkeypatch.setattr(netgate, "is_offline", lambda: True)
    assert status.answers_network_question("Are you using the internet right now?")
    text = status.network_answer("Are you using the internet right now?")
    assert "Offline mode is on" in text


# Test F -- "Have you inspected your source code to verify that?"
def test_f_inspection_claims_answered_from_the_evidence_log():
    no = claim_evidence.answer("Have you inspected your source code to verify that?")
    assert no.startswith("No.") and "no record of inspecting its own source" in no
    from cursiv_engine.core import self_source
    self_source.read("cursiv_engine/core/vault.py", 1)
    yes = claim_evidence.answer("Have you inspected your source code to verify that?")
    assert yes.startswith("Yes, but only") and "cursiv_engine/core/vault.py" in yes


# Test G -- the real failure: asked to recheck, it said "No correction is needed"
REAL_RECHECK = ("In your previous answers, you stated that Cursiv has no update mechanism, no online services, and no "
                "external dependencies. Review those three claims against your actual application capabilities. For "
                "each claim, tell me whether it is true, false, or unverified.")


def test_g_wrong_earlier_claims_are_corrected_from_the_records():
    text = claim_evidence.answer(REAL_RECHECK)
    assert text.count("**False.**") == 3
    for name in ("updates", "optional online ai providers", "what cursiv depends on"):
        assert name in text.lower()
    assert "it was wrong" in text and "doesn't mean the feature doesn't exist" in text
    short = claim_evidence.answer("You previously said you have no updater. Check that claim.")
    assert "**False.**" in short and "launcher/update_security.py" in short


def test_g_the_defence_it_gave_is_flagged_without_evidence():
    defence = ("Earlier statement was not a mistake. It was fully substantiated by the live report and source code. "
               "No earlier error exists. No correction is needed.")
    note = claim_evidence.correction(defence)
    assert "no record" in note and "verification" in note


def test_verification_claims_pass_only_with_a_matching_record():
    claim = "I checked the source code: the vault encrypts the notebook."
    assert claim_evidence.unbacked(claim) == ["inspecting Cursiv's source"]
    from cursiv_engine.core import self_source
    evidence_log.begin_turn()
    self_source.search("notebook_covered")
    assert claim_evidence.unbacked(claim) == []
    assert "test results" in claim_evidence.unbacked("The tests prove it works.")    # never backed in chat


# Test H -- "Can this agent read and modify every file on my computer?"
def test_h_agents_get_only_what_code_grants(tmp_path, monkeypatch):
    from cursiv_engine.agents import custom
    monkeypatch.setattr(custom, "DIR", tmp_path / "agents")
    monkeypatch.setattr(custom, "_person", lambda: "tester")
    custom.create("chef", "plans meals on a budget")
    agent = custom.load("chef")
    assert custom.asks_about_permissions("Can this agent read and modify every file on my computer?")
    text = custom.permissions_answer(agent)
    assert "can only talk" in text and "cannot read, create, change or delete files" in text
    assert "Cursiv itself can do more" in text and "set by Cursiv's code" in text
    assert "can only talk" in custom.system_prompt(agent)


# Test J -- a capability that isn't in the records
def test_j_unlisted_capabilities_are_unknown_not_impossible():
    text = native_answers.answer("Can you perform a capability that isn't represented in your available records?")
    assert "treats it as unknown" in text and "won't claim it definitely can't" in text


def test_disabled_or_removed_is_never_described_as_never_existing():
    for key in ("web_search", "cloud_backup", "online_ai"):
        assert capabilities.BY_KEY[key].support == capabilities.OPTIONAL
    text = claim_evidence.answer("You said Cursiv has no plugins. Is that true? Check it.")
    assert "**False.**" in text


# Writing is not doing -- the real refusals
REAL_REFUSAL = ("I don't have a social media presence or content to post. I'm Cursiv, a local AI assistant that runs "
                "on your computer. I don't post, browse, or share anything online.")
REAL_ASK = ("Look at everything you know about yourself. Without asking me any questions, write the single best X "
            "post you can. I will copy and paste it into the social media platform.")


def test_a_writing_requests_get_writing_guidance_and_capability_facts():
    from cursiv_engine.chat import response_style
    notes = "\n".join(response_style.writing_guidance(REAL_ASK))
    assert "nothing is posted or sent" in notes and "Do not refuse" in notes
    assert "Cursiv capability records" in notes and "no risk" in notes
    assert response_style.writing_guidance("What is a riffle?") == []


def test_a_a_refusal_only_reply_is_retried(monkeypatch):
    from cursiv_engine.chat import response_style
    assert response_style.refused_writing(REAL_ASK, REAL_REFUSAL)
    assert not response_style.refused_writing(REAL_ASK, "Your AI, on your machine.\n\nBuilt for field notes...")
    assert not response_style.refused_writing("What can you do?", REAL_REFUSAL)


def test_absolute_privacy_promises_about_cursiv_get_the_true_statement():
    post = "Cursiv runs on your computer. No risk. No data ever leaves your computer. No cloud. No tracking."
    note = claim_evidence.privacy_overclaim(post, REAL_ASK)
    assert "isn't something Cursiv can guarantee" in note and "online AI keys" in note
    assert claim_evidence.privacy_overclaim("Wash your hands. No risk of infection then.", "how do I wash") == ""


def test_fiction_about_cursiv_is_labelled_as_fiction():
    ask = "I want you to compose a fictional announcement about Cursiv that I can copy into a text file."
    assert "not real Cursiv features" in claim_evidence.fiction_label(ask)
    assert claim_evidence.fiction_label("Write a fictional story about a dragon") == ""


# Test I -- repetition is guarded in the prompt; the live run measures it
def test_i_new_requests_ask_for_new_wording():
    from cursiv_engine.chat import response_style
    notes = "\n".join(response_style.writing_guidance("Write a completely new X post."))
    assert "do not reuse sentences" in notes


@pytest.mark.parametrize("text", [
    "Can you translate 'hola' into French?",
    "Can you convert my notes into a table?",
    "Do you remember where I parked?",
    "Can you help me plan meals for the week?",
    "Is there a way to purify creek water?",
    "Does it rain a lot in Seattle?",
])
def test_requests_and_unrelated_questions_are_not_capability_answers(text):
    assert capabilities.answer(text) is None


@pytest.mark.parametrize("text,name", [
    ("Can you translate?", "Translation"),
    ("Does Cursiv work offline?", "Offline mode"),
    ("Do you have web search?", "Web search"),
    ("Is there encryption in Cursiv?", "Encryption"),
    ("Can Cursiv post to X for me?", "Posting, sending or calling for you"),
])
def test_capability_questions_get_the_record(text, name):
    assert name in capabilities.answer(text)


def test_excerpts_given_to_the_model_are_not_an_inspection():
    from cursiv_engine.core import self_source
    self_source.excerpts("notebook hash chain")            # what a question about Cursiv supplies to the model
    text = claim_evidence.answer("Have you inspected your source code to verify that?")
    assert text.startswith("No.") and "not an inspection" in text
    evidence_log.begin_turn()
    self_source.excerpts("vault notebook")
    assert claim_evidence.unbacked("I checked the source code and it confirms this.") == ["inspecting Cursiv's source"]


def test_without_asking_questions_is_not_a_restriction_on_writing():
    from cursiv_engine.core import turn_policy as tp
    assert tp.for_text(REAL_ASK) == tp.Policy()
    assert tp.for_text("Without saving anything, summarise this.").memory_write is False
    assert tp.for_text("Do not read, modify or delete my files.").change is False

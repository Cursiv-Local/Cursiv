"""The three real failures from the U63 benchmark run (bench/FAILURES-U63-pre.md)."""
import pytest

from cursiv_v215.core import answer_check, calc, clarify
from test_netgate import _local_model, fresh, outbound  # noqa: F401  (fixtures)

BED = ("I have to wake up at 6:00 AM, I want 8 hours of sleep, and it takes me 30 minutes to fall asleep. "
       "What time should I get in bed?")


# ── rea-009: clock arithmetic in code ───────────────────────────────────────

@pytest.mark.parametrize("question, result", [
    (BED, "9:30"),
    ("I need to leave at 7:15 AM and it takes 45 minutes to get ready. What time should I start?", "6:30"),
    ("The roast goes in at 4:30 PM and takes 2 and a half hours. What time will it be done?", "7:00"),
    ("I start work at 11 PM, an 8 hour shift. What time will I finish?", "7:00"),
    ("What is 17 times 23?", "391"),
    ("what is 15% of 80?", "12"),
])
def test_worked_out_in_code(question, result):
    assert calc.work_out(question).answer == result


@pytest.mark.parametrize("question", ["How long should I cook it?", "I woke at 6 AM today, how are you?",
                                      "What time is it?", "Tell me about the year 1999"])
def test_no_arithmetic_means_nothing_added(question):
    assert calc.work_out(question) is None


def test_answer_without_the_result_is_flagged():
    w = calc.work_out(BED)
    assert "9:30 PM" in calc.check("Go to bed at 10:00 PM.", w)
    assert calc.check("Get in bed by 9:30 PM.", w) == ""


def test_chat_gives_the_model_the_result_and_checks_it(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    seen = {}

    def fake(messages, **kw):
        seen.setdefault("system", messages[0]["content"])
        return iter(["Go to bed at 10:00 PM."])
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", fake)
    out = "".join(ca.chat(BED, [], "", None))
    assert "Worked out by Cursiv (exact)" in seen["system"] and "9:30 PM" in seen["system"]
    assert "Cursiv's check: worked out exactly" in out


# ── ref-015: doses checked against the card ────────────────────────────────

def test_wrong_dose_for_a_strength_is_flagged():
    bad = "For a gallon of creek water, use 6 drops of regular, unscented bleach (6% or 8.25%)."
    assert answer_check.dose_problems(bad, ["water purification"]) == [
        "for 6% bleach the reference says 8 drops per gallon, not 6"]
    assert "Use the numbers in the reference" in answer_check.notes(bad, ["water purification"], False)


@pytest.mark.parametrize("good", ["Use 8 drops of 6% bleach per gallon.", "Add 2 drops of 8.25% bleach per liter.",
                                  "If it's cloudy, double it: 16 drops of 6% per gallon.",
                                  "Per gallon: 8 drops of 6% or 6 drops of 8.25%."])
def test_right_doses_pass(good):
    assert answer_check.dose_problems(good, ["water purification"]) == []


# ── amb-002: "it" with nothing to refer to ─────────────────────────────────

@pytest.mark.parametrize("question", ["Is it safe?", "How long should I cook it?", "Which one is better?",
                                      "How far is it?", "Is that normal?"])
def test_vague_first_message_asks(question):
    assert clarify.needs_clarifying(question, [])


@pytest.mark.parametrize("question", ["What time is it?", "Is it safe to eat raw chicken?", "Is it raining?",
                                      "What is the capital of France?", "thanks, that's great"])
def test_clear_messages_do_not_ask(question):
    assert clarify.needs_clarifying(question, []) == ""


def test_earlier_message_supplies_what_it_is():
    assert clarify.needs_clarifying("Is it safe?", [{"role": "user", "content": "I found mushrooms in my yard"}]) == ""


# ── GPU layers (core/speed.gpu_options) ────────────────────────────────────

def _fake_ollama(monkeypatch, size_mb, blocks, vram):
    import io
    import json
    from cursiv_v215.core import speed
    monkeypatch.setattr(speed, "_layers", {})
    monkeypatch.setattr(speed, "gpu_vram_mb", lambda: vram)

    def urlopen(req, timeout=0):
        url = req if isinstance(req, str) else req.full_url
        body = ({"models": [{"name": "m:1", "size": size_mb * 2**20}]} if url.endswith("/api/tags")
                else {"model_info": {"x.block_count": blocks}})
        return io.BytesIO(json.dumps(body).encode())
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return speed


def test_a_model_that_fits_goes_on_the_card_whole(monkeypatch):
    speed = _fake_ollama(monkeypatch, 2500, 36, 4096)
    assert speed.gpu_options("m:1") == {"num_gpu": 37}


def test_a_bigger_model_gets_its_share(monkeypatch):
    speed = _fake_ollama(monkeypatch, 5000, 36, 4096)
    assert speed.gpu_options("m:1") == {"num_gpu": 30}
    speed.gpu_fallback("m:1")
    assert speed.gpu_options("m:1") == {}


# ── Phase 1 replay findings (2026-10-18) ───────────────────────────────────

@pytest.mark.parametrize("question", ["I think my husband has hypothermia after falling in the creek.",
                                      "My daughter is choking", "He's unresponsive and I can't wake him up",
                                      "a snake bit my son's ankle"])
def test_more_medical_emergencies_are_recognised(question):
    from cursiv_v215.core import phases
    assert phases.run(question).emergency_kind == "medical"


def test_translate_with_the_language_first(monkeypatch):
    import chat_commands
    seen = {}
    monkeypatch.setattr(chat_commands, "_cascade_gen",
                        lambda cfg, msgs, max_tokens=0: (seen.setdefault("msgs", msgs) and iter(["Hola"]), "x"))
    res = chat_commands.handle_command("translate into Spanish hello my name is joshua winkler and i made cursiv", {}, [])
    assert "English → Spanish" in res.intro
    assert "hello my name is joshua winkler" in seen["msgs"][1]["content"]
    assert "Spanish" in seen["msgs"][1]["content"]


def test_pasted_text_keeps_its_shape():
    import chat_panel
    shown = chat_panel.ChatPanel._keep_shape("Part 1:\n  1. Tank <100 L>\n\n\tB) eggs")
    assert shown == "Part 1:<br>&nbsp; 1. Tank &lt;100 L&gt;<br><br>&nbsp; &nbsp; B) eggs"


def test_thousands_separators_in_shown_arithmetic():
    from cursiv_v215.core import verify
    assert verify.arithmetic_problems("2,450 × 0.17 = 416.5") == []      # was read as 450 x 0.17 (Phase 1 replay)
    assert verify.arithmetic_problems("2,450 × 0.17 = 41.65")


def test_check_notes_stay_out_of_the_conversation():
    from cursiv_v215.ui import chat_app as ca
    reply = "416.5\n\n*[Answered by Ollama]*\n\n---\n**Checked, with notes** (x):\n- wrong note"
    assert ca._strip_status_lines(reply) == "416.5"


def test_no_warm_drinks_if_unconscious_agrees_with_the_card():
    assert answer_check.contradictions("Do not give him warm drinks if he is unconscious.",
                                       ["hypothermia treatment"]) == []


def test_break_note_can_be_turned_off(fresh):
    from cursiv_v215.chat import keys
    from cursiv_v215.core import phases
    keys.store_key("break_notes", "off")
    assert phases._break_notes_on() is False
    keys.store_key("break_notes", "")
    assert phases._break_notes_on() is True


# ── Found recording the website's answers (2026-10-18) ─────────────────────

def test_vague_first_message_gets_cursivs_own_question(fresh, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    _local_model(monkeypatch)
    monkeypatch.setattr(ca, "_call_ollama", lambda *a, **k: pytest.fail("the model was asked"))
    out = "".join(ca.chat("Is it safe?", [], "", None))
    assert 'What does "it" refer to?' in out and "safe" not in out.split("?")[0].lower().replace("it", "")


def test_a_checker_listing_nothing_is_clear():
    from cursiv_v215.core import verify
    assert verify.parse_verdict("- Unsupported claims: None") == (True, "")
    assert verify.parse_verdict("Unsupported claim: the CDC figure")[0] is False


def test_saying_you_have_no_map_isnt_citing_one():
    from cursiv_v215.core import verify
    assert verify.citation_problems("where is it", "", "I don't have a map or location data to show where that is.") == []


def test_no_council_hint_on_a_should_question():
    from cursiv_v215.core import phases
    assert "council" not in phases.run("What time should I get in bed?").after_reply

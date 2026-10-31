"""The provider recovery buttons appear only beside a provider failure.

The owner reported a permanent "AI Providers…" button under the chat box (U112-U115):
it was created visible and nothing hid it. Settings → AI Providers stays the everyday route.
"""
from test_chat_feedback import panel  # noqa: F401  (fixture)


def _shown(button, panel):
    return button.isVisibleTo(panel)


def test_no_provider_prompt_under_the_chat_box_at_rest(panel):
    assert not _shown(panel._provider_settings_btn, panel)
    assert not _shown(panel._retry_provider_btn, panel)
    assert _shown(panel._input, panel) and _shown(panel._send_btn, panel) and _shown(panel._stop_btn, panel)


def test_provider_failure_offers_recovery_then_a_new_turn_clears_it(panel):
    panel._begin_turn('Explain iron oxidation')
    target = panel._run_target()
    panel._on_run_event(target, dict(kind='provider_failure', run=None,
        text='No API key configured. Add your key in Settings → AI Providers, then retry.',
        prompt='Explain iron oxidation', request=None))
    assert _shown(panel._provider_settings_btn, panel)       # the way to fix it, beside the failure
    assert not _shown(panel._retry_provider_btn, panel)      # nothing preserved, so nothing to retry
    panel._begin_turn('A normal follow-up')
    assert not _shown(panel._provider_settings_btn, panel)


def test_a_completed_turn_without_a_failure_leaves_the_bottom_clean(panel):
    panel._begin_turn('hey how are you')
    panel._on_run_event(panel._run_target(), dict(kind='done', run=None, history=[('user', 'hey how are you')]))
    assert not panel._streaming
    assert not _shown(panel._provider_settings_btn, panel)
    assert not _shown(panel._retry_provider_btn, panel)

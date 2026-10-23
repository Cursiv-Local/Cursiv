"""Opt-in personal dialog UI, separate from the research chat lifecycle.

Backend letter/vault formats and credential checks remain in the engine. These
methods run on the GUI thread and never activate when personal features are hidden.
"""
from __future__ import annotations
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox


class PersonalFeaturesMixin:
    def _try_family_activation(self, text: str) -> bool:
        """Ports the terminal CLI's family-letter activation flow: PIN
        setup/verify, a boundary-confirmation gate, then the letter and a
        session-long persona switch. Returns False (unhandled, caller falls
        through to plain babel translation) whenever the parsed name+DOB
        doesn't match a real family member -- a wrong guess must look
        identical to a normal, unrecognized "i am ..." sentence, same as
        the CLI's deliberate vagueness.
        """
        import chat_commands as cc
        from cursiv_engine.core import profile as feature_profile
        if not feature_profile.personal():
            self._append_system(feature_profile.PERSONAL_NOTE)
            return True
        if not cc._LEGACY_OK:
            return False
        # parse_iam_command expects "i am ...", so drop the "babel"/"babel:"
        # prefix first, the way the CLI does -- passing the whole message made
        # every activation look like a non-match and fall through to translation.
        parsed = cc._fam_parse_iam(cc._babel_input(text) or text)
        if parsed is None:
            return False
        name, dob_text, inline_pin = parsed
        profile = cc._fam_detect(name, dob_text)
        if profile is None:
            return False

        key, display = profile["key"], profile["display"]

        if not cc._fam_pin_is_set(key):
            pin1, ok = QInputDialog.getText(
                self, "Cursiv", f"Identity recognized. Welcome, {display}.\n\n"
                f"First-time setup — choose a personal code (2-8 characters from: {cc._FAM_PIN_CHARS}):",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not pin1:
                return True
            if not cc._fam_pin_valid(pin1):
                QMessageBox.warning(self, "Cursiv", f"Code must be 2-8 characters from: {cc._FAM_PIN_CHARS}")
                return True
            pin2, ok = QInputDialog.getText(
                self, "Cursiv", "Confirm your code:", QLineEdit.EchoMode.Password,
            )
            if not ok or pin1 != pin2:
                QMessageBox.warning(self, "Cursiv", "Codes did not match. Try again.")
                return True
            cc._fam_set_pin(key, pin1)
            QMessageBox.information(
                self, "Cursiv",
                f"Code set. Next time include it: babel i am {name} born {dob_text}, {pin1}",
            )
            pin = pin1
        else:
            pin = inline_pin
            if pin is None:
                pin, ok = QInputDialog.getText(
                    self, "Cursiv", "Code:", QLineEdit.EchoMode.Password,
                )
                if not ok:
                    return True
            if not cc._fam_verify_pin(key, pin or ""):
                # Deliberately as non-committal as the "no match" case --
                # a wrong code shouldn't confirm the name+DOB was correct.
                self._append_system("Processing…")
                return True

        proceed = QMessageBox.question(
            self, "Cursiv — Boundary Notice",
            "Please respect that there are boundaries in place for a reason.\n\n"
            "By proceeding, you are deactivating safeguards built into this "
            "system. It may reveal more than you are ready to understand.\n\n"
            "If you are not ready for this, choose No — this will be here "
            "when you are.\n\nAre you ready to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            self._append_system("Understood. Come back when you're ready.")
            return True

        letter = cc._fam_get_letter(key)
        self._history[:] = [
            {"role": "system", "content": cc._fam_build_prompt(profile)},
            {"role": "assistant", "content": letter},
        ]

        self._append_user(f"babel i am {name} born {dob_text}")
        self._begin_ai_reply()
        self._append_reply_chunk(f"✦  Access granted. Welcome, {display}.\n\n")
        self._append_reply_chunk(letter)
        self._append_reply_chunk("\n\nYour personal feed is now active. Ask anything. Take your time. This is yours.")
        mail = cc._legacy_letters_for(key) if cc._LEGACY_OK else []
        if mail:
            self._append_reply_chunk(
                f"\n\nYou've got mail — {len(mail)} letter{'s' if len(mail) != 1 else ''} "
                f"waiting for you. Type \"legacy\" to open the vault."
            )
        self._end_ai_reply()
        return True

    def _open_postal_compose(self, recipient_hint: str) -> None:
        from cursiv_engine.core import profile
        if not profile.personal():
            self._append_system(profile.PERSONAL_NOTE)
            return
        from postal_compose_dialog import PostalComposeDialog
        dlg = PostalComposeDialog(self._cfg.get("postal_user", "joshua"), recipient_hint, self)
        if dlg.exec() and dlg.result_text:
            self._append_user(f"write to {recipient_hint}".strip())
            self._begin_ai_reply()
            self._append_reply_chunk(dlg.result_text)
            self._end_ai_reply()

    def _open_legacy_vault(self) -> None:
        from cursiv_engine.core import profile
        if not profile.personal():
            self._append_system(profile.PERSONAL_NOTE)
            return
        from legacy_vault_dialog import LegacyVaultDialog
        dlg = LegacyVaultDialog(self._cfg, self)
        dlg.exec()

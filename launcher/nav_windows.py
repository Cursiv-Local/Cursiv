"""
The sidebar's destinations besides Chat: Memory & Knowledge, Tools and Help.

Each is a plain window. Every entry says in one sentence what it does, and its
button opens the existing dialog or puts the right command in the chat box,
so nothing here re-implements a feature (docs/COMMAND-INVENTORY.md).
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QTextBrowser, QVBoxLayout, QWidget,
)

import theme

_QSS = f"""
QDialog {{ background: {theme.BG}; color: {theme.TEXT}; }}
QLabel {{ background: transparent; color: {theme.TEXT}; }}
QLabel#title {{ font-size: 20px; font-weight: 650; }}
QLabel#explain {{ color: {theme.MUTED}; font-size: 13px; }}
QLabel#name {{ font-size: 14px; font-weight: 600; }}
QLabel#section {{ color: {theme.FAINT}; font-size: 12px; font-weight: 600; padding-top: 8px; }}
QFrame#card {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 10px; }}
QCheckBox {{ font-size: 14px; font-weight: 600; background: transparent; }}
QListWidget {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 8px; }}
QListWidget::item {{ padding: 6px 8px; }}
QListWidget::item:selected {{ background: {theme.SURFACE2}; color: {theme.TEXT}; }}
QTextBrowser {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 8px; padding: 10px; }}
"""


class _Window(QDialog):
    def __init__(self, parent, title: str, intro: str, width: int = 720, height: int = 620):
        super().__init__(parent)
        self._win = parent
        self.setWindowTitle(f"Cursiv — {title}")
        self.resize(width, height)
        self.setStyleSheet(_QSS)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 16)
        outer.setSpacing(10)
        t = QLabel(title); t.setObjectName("title"); outer.addWidget(t)
        outer.addWidget(self._explain(intro))
        inner = QWidget()
        self.body = QVBoxLayout(inner); self.body.setContentsMargins(0, 6, 0, 0); self.body.setSpacing(10)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        foot = QHBoxLayout(); foot.addStretch(1)
        close = QPushButton("Close"); close.setStyleSheet(theme.ghost_button()); close.clicked.connect(self.accept)
        foot.addWidget(close)
        outer.addLayout(foot)

    @staticmethod
    def _explain(text: str) -> QLabel:
        lbl = QLabel(text); lbl.setObjectName("explain"); lbl.setWordWrap(True)
        return lbl

    def section(self, text: str) -> None:
        lbl = QLabel(text); lbl.setObjectName("section"); self.body.addWidget(lbl)

    def entry(self, name: str, explain: str, button: str, handler, layout=None) -> QPushButton:
        card = QFrame(); card.setObjectName("card")
        row = QHBoxLayout(card); row.setContentsMargins(16, 12, 16, 12); row.setSpacing(12)
        text = QVBoxLayout(); text.setSpacing(2)
        n = QLabel(name); n.setObjectName("name"); text.addWidget(n)
        text.addWidget(self._explain(explain))
        row.addLayout(text, 1)
        btn = QPushButton(button); btn.setStyleSheet(theme.ghost_button())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(handler)
        row.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        (layout or self.body).addWidget(card)
        return btn

    # helpers that act on the main window / chat panel
    def _panel(self):
        return getattr(self._win, "_chat_panel", None)

    def _prefill(self, text: str):
        def go():
            p = self._panel()
            if p is not None:
                p.prefill(text)
            self.accept()
        return go

    def _send(self, text: str):
        def go():
            p = self._panel()
            if p is not None:
                p._quick_send(text)
            self.accept()
        return go

    def _window(self, name: str, *args):
        def go():
            fn = getattr(self._win, name, None) or getattr(self._panel(), name, None)
            if fn:
                fn(*args)
        return go


class KnowledgeDialog(_Window):
    def __init__(self, parent=None):
        super().__init__(parent, "Memory & Knowledge",
                         "What Cursiv knows about you, and the reference material it can quote. It's stored on this computer; an online AI, if you use one, gets the memories relevant to each message.",
                         width=820, height=680)
        self.section("MEMORY")
        self.entry("What Cursiv remembers",
                   "Every saved fact, where it came from (you said it, or Cursiv inferred it) and when. Remove any of them.",
                   "Open", self._window("_open_memory"))
        try:
            from cursiv_v215.memory import semantic
            card = QFrame(); card.setObjectName("card")
            v = QVBoxLayout(card); v.setContentsMargins(16, 12, 16, 12)
            box = QCheckBox("Learn from our conversations"); box.setChecked(semantic.learning_enabled())
            box.toggled.connect(semantic.set_learning); v.addWidget(box)
            v.addWidget(self._explain("On: Cursiv saves lasting facts it notices (marked inferred). "
                                      "Off: it only remembers what you tell it with \"remember …\"."))
            self.body.addWidget(card)
        except Exception:
            pass
        self.entry("Saved notes", "Browse, search and expand the answers you kept with \"save this\".", "Open", self._open_notes)

        self.section("YOUR DOCUMENTS")
        self.body.addWidget(self._explain(
            "Protocols, SOPs, permits and field guides you import (PDF, TXT, MD). Cursiv quotes them by page, and each "
            "file is fingerprinted so you can show which version was used. The original file isn't changed."))
        self._build_documents()

        self.section("OFFLINE REFERENCE")
        self.body.addWidget(self._explain(
            "Short entries on survival, first aid and science that Cursiv shows word for word when a question matches. "
            "Sourced entries name their source; none has been reviewed by a medical professional yet."))
        self._build_reference()

    def _open_notes(self):
        panel = self._panel()
        self.accept()
        if panel is not None:
            panel._open_saved_notes()

    def _build_documents(self):
        from cursiv_v215.core import documents
        self._doc_list = QListWidget(); self._doc_list.setMinimumHeight(110)
        self.body.addWidget(self._doc_list)
        row = QHBoxLayout()
        add = QPushButton("Import a document…"); add.setStyleSheet(theme.ghost_button())
        rm = QPushButton("Remove selected"); rm.setStyleSheet(theme.ghost_button())
        self._doc_status = QLabel(""); self._doc_status.setWordWrap(True)
        row.addWidget(add); row.addWidget(rm); row.addWidget(self._doc_status, 1)
        holder = QWidget(); holder.setLayout(row); self.body.addWidget(holder)

        def fill():
            self._doc_list.clear()
            for d in documents.library():
                it = QListWidgetItem(f"{d['name']}  ·  {d['pages']} pages  ·  imported {d['imported']}  ·  "
                                     f"fingerprint {d['fingerprint'][:16]}")
                it.setData(Qt.ItemDataRole.UserRole, d["id"])
                self._doc_list.addItem(it)
            if not self._doc_list.count():
                self._doc_list.addItem("No documents yet.")

        def do_add():
            from PyQt6.QtWidgets import QFileDialog
            paths, _ = QFileDialog.getOpenFileNames(self, "Import documents", "", "Documents (*.pdf *.txt *.md *.csv)")
            done, failed = 0, []
            for p in paths:
                try:
                    documents.add(p); done += 1
                except (ValueError, OSError) as exc:
                    failed.append(f"{p.split('/')[-1]}: {exc}")
            self._doc_status.setText(f"Imported {done}." + (" Not imported: " + "; ".join(failed) if failed else ""))
            fill()

        def do_remove():
            it = self._doc_list.currentItem()
            doc_id = it.data(Qt.ItemDataRole.UserRole) if it else None
            if doc_id and documents.remove(doc_id):
                self._doc_status.setText("Removed from Cursiv's library (the original file is untouched).")
                fill()
        add.clicked.connect(do_add); rm.clicked.connect(do_remove)
        fill()

    def _build_reference(self):
        from cursiv_v215.core import reference
        search = QLineEdit(); search.setPlaceholderText("Search the reference…")
        self.body.addWidget(search)
        row = QHBoxLayout()
        self._list = QListWidget(); self._list.setMinimumHeight(240); self._list.setMaximumWidth(280)
        self._text = QTextBrowser(); self._text.setMinimumHeight(240)
        row.addWidget(self._list); row.addWidget(self._text, 1)
        holder = QWidget(); holder.setLayout(row); self.body.addWidget(holder)
        self._entries = reference.entries()
        self._held = reference.NOT_IN_CHAT

        def fill(q: str = ""):
            self._list.clear()
            for e in self._entries:
                if q and q.lower() not in (e.title + " " + e.text).lower():
                    continue
                it = QListWidgetItem(f"{e.title}  ·  {e.category}")
                it.setData(Qt.ItemDataRole.UserRole, e)
                self._list.addItem(it)
        def show(item):
            if item is None:
                return
            e = item.data(Qt.ItemDataRole.UserRole)
            held = ("<p style='color:%s'><b>Held back from chat</b> until someone qualified reviews it.</p>"
                    % theme.AMBER) if e.title in self._held else ""
            src = reference.source(e.title)
            where = ""
            if src:
                review = "reviewed by a professional" if src.get("reviewed") else "not yet reviewed by a professional"
                where = (f"<p style='color:{theme.MUTED}'>Source: <a href='{src.get('url', '')}'>{src.get('source', '')}</a>"
                         f" · checked {src.get('checked', '?')} · {review}</p>")
            self._text.setHtml(f"<h3>{e.title}</h3><p style='color:{theme.MUTED}'>{e.id}</p>{held}<p>{e.text}</p>{where}")
        search.textChanged.connect(fill)
        self._list.currentItemChanged.connect(lambda cur, _prev: show(cur))
        fill()
        if self._list.count():
            self._list.setCurrentRow(0)


class ToolsDialog(_Window):
    def __init__(self, parent=None):
        super().__init__(parent, "Tools",
                         "Extra things Cursiv can do. Each one opens its own window or puts a starting command in the chat box.",
                         width=760, height=680)
        try:
            from cursiv_v215.core import profile as _profile
            personal = _profile.personal()
        except Exception:
            personal = False
        self.section("FIELD WORK")
        self.entry("Field Notebook", "Record observations with sample IDs and coordinates; corrections never overwrite.",
                   "Open", self._window("_open_field_notebook"))
        self.entry("Field report", "A printable summary of what was recorded, by site, with every entry's fingerprint.",
                   "Make", self._send("field report"))
        self.entry("Your documents", "Import a protocol or SOP; answers quote it by page.", "Start",
                   self._prefill("add document "))
        self.entry("Calculations", "Units, coordinates and UTM, distance and bearing, dilutions, statistics: worked "
                   "out in code.", "Start", self._prefill("distance from 44.1234, -71.5678 to 44.1300, -71.5600"))
        self.entry("Field demo", "Try everything with sample data, kept apart from your own records (demo off to end).",
                   "Start", self._send("demo"))
        self.section("EVERYDAY")
        if personal:
            self.entry("Write a family letter", "A private letter that opens only with the code you set for that person.",
                       "Write", self._window("_open_postal_compose", ""))
            self.entry("Read letters", "Letters waiting for you, and ones you've sent.", "Show", self._send("letters"))
            self.entry("Legacy Vault", "Keep family stories and messages for later, behind a PIN.", "Open",
                       self._window("_open_legacy_vault"))
        self.entry("Translate", "Type your text, then the language: translate good morning into Spanish.",
                   "Start", self._prefill("translate  into Spanish"))
        if personal:
            self.entry("Phone app", "Link your phone so you can ask about photos and continue the chat here.",
                       "Open", self._window("_open_phone"))
        import sys as _sys
        if _sys.platform == "win32":             # the USB edition is Windows-only for now
            self.entry("Make a Cursiv USB", "Copy Cursiv, its AI engine and models to a USB drive to run on any "
                       "Windows PC.", "Open", self._window("_open_usb_maker"))
        if not personal:
            self.body.addWidget(self._explain("Personal features are hidden: Settings → Appearance."))
            return
        self.section("CODING AND BIG QUESTIONS")
        self.entry("Coding help", "Step-by-step help with code; uses local coding models if installed.",
                   "Start", self._prefill("codex "))
        self.entry("Ask the council", "Several AI views on a hard question, combined into one answer. Slower.",
                   "Start", self._prefill("council "))
        self.entry("Your agents", "Specialists you create (agent new name: job) and talk to with @name.",
                   "Show", self._send("agents"))

        self.section("ADVANCED")
        self._adv = QWidget(); adv = QVBoxLayout(self._adv); adv.setContentsMargins(0, 0, 0, 0); adv.setSpacing(10)
        self.entry("Training data", "Examples for training a small personal model (LoRA).", "Open",
                   self._window("_open_training_data"), layout=adv)
        self.entry("Plugins", "Abilities Cursiv wrote for itself, after you approved them.", "Show", self._send("plugins"), layout=adv)
        self.entry("Write a new ability", "Cursiv writes a plugin, tests it in a sandbox, and installs it only if you approve.",
                   "Start", self._prefill("evolve "), layout=adv)
        self.entry("Projects", "Running summaries of things you're working on.", "Show", self._send("projects"), layout=adv)
        self.entry("Make an image", "Needs a paid OpenAI key or a free Cloudflare account.", "Start",
                   self._prefill("image "), layout=adv)
        toggle = QPushButton("Show advanced tools"); toggle.setStyleSheet(theme.ghost_button())
        toggle.setCheckable(True)
        toggle.toggled.connect(lambda on: (self._adv.setVisible(on),
                                           toggle.setText("Hide advanced tools" if on else "Show advanced tools")))
        self.body.addWidget(toggle)
        self.body.addWidget(self._adv)
        self._adv.setVisible(False)


class HelpDialog(_Window):
    def __init__(self, parent=None):
        super().__init__(parent, "Help", "How Cursiv works, in plain language.", width=760, height=680)
        view = QTextBrowser(); view.setOpenExternalLinks(True); view.setMinimumHeight(480)
        view.setMarkdown(self._guide())
        self.body.addWidget(view, 1)

    @staticmethod
    def _guide() -> str:
        parts = [
            "## The basics",
            "Just type a question and press **Enter**. Cursiv answers with an AI model that runs on this computer.",
            "",
            "- The **badge at the top right** shows what can go online: *LOCAL ONLY · internet blocked* when offline "
            "mode is on. Click it to change.",
            "- The **menu at the top left** shows the AI model answering on this computer.",
            "- Under each answer, a **Sources** line says what the answer was given: Cursiv Offline Reference, your "
            "documents (with pages), Cursiv's own calculations, or *model knowledge (not checked against a source)*. "
            "Cursiv writes that line from its own records, never the AI.",
            "- **● Local** means the answer came from your computer; **● Online** means a service you set up.",
            "- A grey box above an answer is Cursiv's **offline reference**, shown word for word.",
            "- **Field Notebook** (sidebar) records observations; type `demo` to try it with sample data.",
            "- Complex answers end with **Known / Inferred / Assumed / Unknown**, so you can see what's a fact and what's a guess.",
            "",
            "## Keeping things private",
            "Turn on **Offline mode** in Settings (or type `offline on`) and Cursiv makes no internet connections. "
            "Web search happens only when you start a message with `search:`.",
            "",
            "## Typed commands",
            "You never need these, but they're quick:",
            "",
        ]
        try:
            import chat_commands as cc
            parts += ["```", cc.help_text("").strip(), "```", ""]
            for key, (title, body) in cc._HELP_TOPICS.items():
                if key in cc._BUILDER_TOPICS and not cc._is_builder():
                    continue
                if key in cc._PERSONAL_TOPICS and not cc._personal():
                    continue
                parts += [f"**{title}**", "```", body.rstrip(), "```", ""]
        except Exception:
            parts.append("Type `help` in the chat to see them.")
        parts += [
            "## If something goes wrong",
            "- **No answer / \"Ollama isn't running\"**: open Settings → Help & diagnostics → Setup and engine, and click Restart Ollama.",
            "- **Very slow**: pick a smaller model in the model menu, or add a free Gemini or Groq key in Settings.",
            "- **Wrong answer**: small local models make mistakes. Check anything important, especially health, money and legal questions.",
            "- Still stuck: Settings → Help & diagnostics → Send a problem report.",
        ]
        return "\n".join(parts)


class WelcomeDialog(_Window):
    """First run (and tray → Getting Started): what Cursiv is, in four lines."""

    def __init__(self, parent=None, setup_needed: bool = False):
        try:
            from cursiv_v215.core import profile as _profile
            personal = _profile.personal()
        except Exception:
            personal = False
        super().__init__(parent, "Welcome to Cursiv",
                         "A personal AI assistant that runs on this computer." if personal else
                         "An AI assistant for field research that runs on this computer.", width=600, height=520)
        points = (
            ("It runs here", "Answers come from an AI model on this computer. The badge at the top right always "
                             "shows what, if anything, can go online; LOCAL ONLY blocks the internet."),
            ("It says where answers come from", "Each answer ends with its sources: the offline reference, your "
                                                "documents, Cursiv's own calculations, or model knowledge."),
            ("A field notebook", "Observations kept exactly as typed, fingerprinted, never overwritten, exported "
                                 "to CSV, JSON and GeoJSON. Type demo to try it with sample data."),
            ("Help is one click away", "The sidebar has Field Notebook, Tools, Settings and Help. Or just type."),
        ) if not personal else (
            ("It runs here", "Answers come from an AI model on this computer. The pill at the top right always "
                             "shows what, if anything, can go online."),
            ("It tells you how sure it is", "Complex answers end with what's known, inferred, assumed and unknown. "
                                            "It can still be wrong, so check what matters."),
            ("It remembers what you tell it", "Say \"remember …\" and it keeps it. Memory & Knowledge shows "
                                              "everything it knows, and you can remove anything."),
            ("Help is one click away", "The sidebar has Tools, Settings and Help. Or just type your question."),
        )
        for name, text in points:
            card = QFrame(); card.setObjectName("card")
            v = QVBoxLayout(card); v.setContentsMargins(16, 12, 16, 12); v.setSpacing(2)
            n = QLabel(name); n.setObjectName("name"); v.addWidget(n)
            v.addWidget(self._explain(text))
            self.body.addWidget(card)
        self._again = QCheckBox("Don't show this again")
        self._again.setChecked(True)
        self.body.addWidget(self._again)
        if setup_needed:
            self.body.addWidget(self._explain("Cursiv still needs an AI model. Setup installs the free local engine "
                                              "and a model sized for this computer."))
            go = QPushButton("Open Setup"); go.setStyleSheet(theme.primary_button())
            go.clicked.connect(lambda: (self.accept(), self._window("_open_setup")()))
            self.body.addWidget(go, 0, Qt.AlignmentFlag.AlignLeft)

    def dont_show_again(self) -> bool:
        return self._again.isChecked()

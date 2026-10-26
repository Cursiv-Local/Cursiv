# Recovery procedures (U102)

What to do when something reads as damaged. Cursiv never repairs or deletes your data on its own; each
step below is yours to take, and none overwrites the original.

## "Conversations and memories are locked" / wrong passphrase
Cursiv can't read encrypted stores without the passphrase and never treats them as empty. Restart and
enter it again. There is no back door: without the passphrase the data can't be recovered.

## A store is damaged (an error instead of your memories, notes or history)
1. `status` lists damaged lines in saved notes and session history (they're kept, just not used).
2. Encryption keeps a copy of every store as it was just before it was first encrypted
   (`.vault-recovery/`, encrypted). From Python, with Cursiv closed and unlocked in that session:
   `vault_migration.recovery_copies(root)` lists them; `vault_migration.write_recovery_copy(root,
   "memory_facts.jsonl", Path("recovered.jsonl"))` writes one to a NEW file after checking its SHA-256.
   It won't overwrite a file and refuses a tampered copy. Compare it with the damaged store before
   deciding what to keep. (A menu item for this is planned; it isn't in U102.)

## The accounts list is damaged
Cursiv uses `accounts.json.bak` automatically and puts it back. If both are damaged it says so and the
primary login still works; extra logins can be added again from Settings.

## The field notebook check reports a problem
`field log check` names the entry and what's wrong (changed, missing, reordered, a cut-off line). Nothing
is fixed automatically. A power cut can cut off only the last entry; later entries start on a new line.
Use the Field Notebook window's Correct to add a correction; the original stays.

## A phone upload too big to encrypt
The receiver lists them in `fieldlog/received-large/`. Delete them once their entries are in your notebook.

## A USB drive was unplugged during a write
Every save writes a temporary file and swaps it in, so a file is the old version or the new one. Run
`status` and `field log check` on the drive before carrying on.

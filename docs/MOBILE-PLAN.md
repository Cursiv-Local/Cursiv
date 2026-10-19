# Cursiv Mobile: plan and decisions

Decided by Joshua, 2026-10-19. The audit behind this: the phone notebook already exists as an
offline web app (`website/notebook/`, docs/PHONE-NOTEBOOK.md); it writes the laptop's own
record format and is imported through the same checks.

## Decisions

| Question | Decision |
|---|---|
| Web app pilot or native first | **Pilot the existing web app first** (live at cursiv.winklers-llc.com/notebook) |
| Native framework | **Expo (React Native)**: reuses `core.js`, builds iOS in the cloud without a Mac |
| App store accounts | Apple Developer ($99/yr) and Google Play ($25) **next month**; the native app waits for them |
| Location | **Optional, per team.** Cursiv records where an observation was made. It is **not** a locating, tracking or safety tool and must never be described as one: teams use their own GPS and tracking systems for that |
| Photo size limit | Not decided by Joshua; the default below applies until a team needs otherwise |
| AI use case | Chosen: **suggested tags** (below) |
| Key revocation | Default below |

## Defaults chosen (change any time)

- **Photos:** keep the original, never shrink it silently. Warn above 15 MB per photo; refuse above
  50 MB (phone and laptop). A phone photo is usually 2–6 MB.
- **Key revocation:** the person who imports into the laptop (normally the team lead) can mark a
  phone's or laptop's key as revoked, with a reason, when a device is lost, stolen or retired.
  After that, new files signed by that key are refused; everything imported before stays, marked
  "signed by a key revoked on <date>". Nothing is deleted.
- **First AI use case: suggested tags.** For an entry or a day, the on-device model suggests a few
  keywords (habitat, taxon group, condition: "riffle", "algae", "turbid") that the person can tap
  to accept. Why this one: short output a person checks at a glance, useful for search and
  reports, low risk if wrong, and it runs on the smallest models. Suggestions are separate,
  signed records marked "AI suggestion · model name"; accepting one adds the tag as the person's
  own entry or correction. Nothing generated changes an observation or is shown as verified.

## Order

1. **Now: pilot the web app** on real phones (one iPhone, one Android): daily sends, the reliability
   checks in docs/PHONE-NOTEBOOK.md, and count any lost entries.
2. **Format hardening** (small): schema version on entries, optional structured GPS accuracy,
   revocation, photo limits, clock-difference flag at import.
3. **Zip send file** (bundle format 2) so large photo sets don't have to fit in the phone's memory.
4. **Expo app** (after the store accounts): the same records and send file, SQLite, keys in the
   phone's secure storage, TestFlight and an Android test track for the pilot.
5. **Suggested tags on the phone**, only after the Expo app has been used in a pilot. Model copied
   from the laptop by USB (no download needed); Apache-2.0 models (Qwen2.5 0.5B/1.5B) by default.

## Not now

On-device AI before step 4 is in use; live network sync or a master node; any location tracking or
team-position feature; cloud backup or phone accounts; editing or deleting past entries; a public
app-store release before a pilot.

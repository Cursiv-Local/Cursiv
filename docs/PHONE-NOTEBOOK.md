# The phone notebook

Record field observations on a phone with no signal, then send them to Cursiv on the
laptop. Status: **built and tested in code and in a desktop browser; not yet used on a
phone in the field.**

## How it works

- **Open once with internet:** `https://cursiv.winklers-llc.com/notebook/`, then "Add to Home
  Screen". After that it opens and works with no signal (its files are kept on the phone).
- **Everything stays on the phone** (the browser's IndexedDB storage). The page makes no
  network requests with your data; there is no account and no server copy.
- Each entry has: observer, site, sample ID, location (typed, or the phone's GPS with its
  accuracy, "phone GPS ±6 m"), measurements kept exactly as typed, notes, photos.
  Corrections are new entries with a reason; the original stays.
- **Send to laptop** makes one `.cursivsync` file. Move it with a USB cable, AirDrop or Quick
  Share (both work without internet). In Cursiv: Field Notebook → Import from team → From the
  phone notebook, or `field log import <file>`.

## One record format, not a second system

The phone writes **exactly the laptop's field-log entry format** (`core/fieldlog.py`): the same
fields, the same SHA-256 chain, photos named by their SHA-256, and a head signed with the phone's
own Ed25519 key, like `core/devicekey.py`. Cursiv imports it through the **same code** as a
laptop's USB share (`fieldsync.import_phone_bundle` unpacks it and calls `import_folder`):
chain and fingerprints checked, signature checked, the phone's key remembered after the first
import, photos checked against their names, nothing merged or overwritten.

`tests/test_phone_notebook.py` runs the phone's own code (`website/notebook/core.js`) under
Node.js to build a log (accented text, integer and decimal values, a photo, a correction), and
Cursiv's Python verifies every fingerprint and the signature. A changed file is refused.

## What a fingerprint and a signature do and don't prove

- A **fingerprint** shows a record hasn't been changed since it was saved.
- A **signature** shows which device's key signed the log, and that nothing was added or removed
  after signing.
- **Neither shows the observation is true.** A person can type a wrong value; a phone's clock
  can be wrong (entries carry the phone's time; Cursiv doesn't correct it). The records are
  attributable and tamper-evident, not verified facts.

## Reliable storage: what's done, what's tested, what isn't

Done:
- Each save waits until the browser confirms it's on disk ("strict" durability) before showing
  "Saved", so closing the app or the battery dying right after doesn't lose it.
- The app asks the browser to keep its storage ("persistent storage").
- The screen always shows how many entries haven't been sent to the laptop.
- The send file is also a backup: every send contains the whole log.

Tested (desktop Chromium, 2026-10-19): entries saved, page reloaded, entries and chain intact;
a correction; the send file imported into Cursiv with its signature checked.

**Not yet tested:** on real iPhones and Android phones; a phone running out of battery mid-save;
months of use. **Known risk:** browsers, iPhones especially, may clear a web app's storage if
it isn't used for weeks, and clearing the browser's data or removing the app deletes anything
not yet sent. Until it's proven on phones: **send to the laptop at the end of every day**, and
treat the phone as a capture tool, not the archive. A native app (needs app-store accounts)
would remove this risk; that's the planned next step if teams use it.

## Privacy

- The page can use the GPS and the camera; the rest of the website can't (separate
  `Permissions-Policy` for `/notebook/`).
- Location is optional (per team), read only when you press "Use this phone's GPS", and only stored in
  that entry. It records where an observation was made. **The notebook is not a locating, tracking
  or safety tool**, and nothing about it has been tested for that: teams use their own GPS and
  tracking systems.
- No data leaves the phone except in the file you choose to send.

# Release runbook

The exact sequence used for U94 and U95. Run in Git Bash from the repository root.
Replace `U96` / `3.14-U96` with the release being made. Each step stops on failure;
never skip a gate. Nothing here copies the owner's private key or personal data.

## 0. One-time setup per clone

```bash
git config core.hooksPath .githooks
```

The pre-commit hook runs the USB gate (`python -m pytest tests -m usb`) before every commit.

## 1. Change, commit, PR, merge

```bash
git switch -c claude/my-change origin/main
python -m pytest tests -q
git add -A && git commit -m "Describe the change"
git push -u origin claude/my-change
gh pr create --repo Cursiv-Local/Cursiv --base main --fill
gh pr checks --repo Cursiv-Local/Cursiv --watch
gh pr merge --repo Cursiv-Local/Cursiv --merge
```

Branches are deleted automatically after merge.

## 2. Prepare the version (its own PR, like step 1)

Set the same version in all three files, then add a `CHANGELOG.md` entry and
`docs/RELEASE-U96.md`:

- `cursiv_engine/core/selfknow.py` → `VERSION = "3.14-U96"`
- `launcher/cursiv_launcher.py` → `_CURRENT_VERSION = "3.14-U96"`
- `installer/cursiv_setup.iss` → header lines, `#define AppVer "3.14-U96"`, `OutputBaseFilename=Cursiv-Setup-3.14-U96`

## 3. Tag the merged commit (after main CI passes)

```bash
git switch main && git pull --ff-only
gh run list --repo Cursiv-Local/Cursiv --commit "$(git rev-parse HEAD)" --workflow tests.yml
git tag -a v3.14-U96 -m "Cursiv v3.14-U96 — <title>; Windows and macOS CI passed"
git push origin v3.14-U96
```

## 4. Build native packages on the locked hosted runners

```bash
gh workflow run windows-build.yml --repo Cursiv-Local/Cursiv -f ref=v3.14-U96
gh workflow run mac-build.yml --repo Cursiv-Local/Cursiv -f ref=v3.14-U96 -f upload=false
```

Record both returned run IDs. Windows uses the existing `build_release.py` from
the immutable tag and requires exact-main CI, the hash-locked environment, frozen
self-test, portable USB-layout self-test, Inno Setup, checksums and provenance.
Its artifact includes `frozen-selftest.txt` and `portable-selftest.txt`. Mac retains
its native test/build/self-test gates. Neither build uses the owner's records or keys.

The former temporary U88 build environment can expire. Do not silently rebuild it
or package with system dependencies that fail `release_provenance.check_lock`.
Hosted builds install the exact lock. Local source tests with an existing Python
installation are a separate measurement and do not replace native release gates.

## 5. Collect and check the eight assets

```bash
R=release-u96; mkdir -p "$R/mac" "$R/assets"
RUN=<verified-Mac-build-run-id>
WIN_RUN=<verified-Windows-build-run-id>
gh run watch "$RUN" --repo Cursiv-Local/Cursiv --exit-status && gh run download "$RUN" --repo Cursiv-Local/Cursiv --dir "$R/mac"
gh run watch "$WIN_RUN" --repo Cursiv-Local/Cursiv --exit-status && gh run download "$WIN_RUN" --repo Cursiv-Local/Cursiv --dir "$R/windows"
O="$R/windows/cursiv-windows"; A="$R/assets"; M="$R/mac/cursiv-mac"
cp "$O/Cursiv-Setup-3.14-U96.exe" "$A/" && cp "$O/Cursiv-Setup-3.14-U96.exe" "$A/Cursiv-Setup-latest.exe"
cp "$O/SHA256SUMS-3.14-U96.txt" "$A/SHA256SUMS.txt" && cp "$O/provenance-3.14-U96.json" "$A/"
cp "$M/Cursiv-3.14-U96-mac-arm64.dmg" "$A/" && cp "$M/Cursiv-3.14-U96-mac-arm64.dmg" "$A/Cursiv-mac-latest.dmg"
cp "$M/SHA256SUMS-mac.txt" "$M/provenance-mac.json" "$A/"
(cd "$A" && tr -d '\r' < SHA256SUMS.txt | sha256sum -c && sha256sum -c SHA256SUMS-mac.txt)
grep -c "ALL PASSED" "$M/selftest.txt"
```

Both provenance files must name the tagged commit (`git rev-parse v3.14-U96^{commit}`).

## 6. Sign with the owner key (never copy it)

The key and the reviewed signer live in Codex's packaged-app folder (see
[OWNER-RELEASE-SIGNING](OWNER-RELEASE-SIGNING.md)). Check the signer first, then sign.

```bash
S="$LOCALAPPDATA/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/CursivReleaseSigning"
(cd "$S/signer" && sha256sum scripts/owner_release.py cursiv_v215/core/release_identity.py cursiv_v215/core/release_public_key.json)
cat "$S/signer/trusted-tool-manifest.json"
V="$LOCALAPPDATA/Programs/Python/Python313/python.exe"
C=$(git rev-parse v3.14-U96^{commit})
(cd "$A" && LOCALAPPDATA="$(cygpath -w "$S/..")" "$V" -I "$S/signer/scripts/owner_release.py" sign \
  --version 3.14-U96 --commit "$C" --output owner-release.json \
  Cursiv-Setup-3.14-U96.exe Cursiv-Setup-latest.exe SHA256SUMS.txt provenance-3.14-U96.json \
  Cursiv-3.14-U96-mac-arm64.dmg Cursiv-mac-latest.dmg SHA256SUMS-mac.txt provenance-mac.json)
cp website/assets/cursiv-owner-release-key.json "$A/"
```

The three signer hashes must equal the manifest. Write `$A/u96-release-verification.json`
in the same shape as the U95 one (versions, CI run links, test counts, `ALL PASSED`).

## 7. Publish the GitHub release (11 assets)

```bash
gh release create v3.14-U96 --repo Cursiv-Local/Cursiv --verify-tag --latest \
  --title "Cursiv v3.14-U96 — <title>" --notes-file docs/RELEASE-U96.md "$A"/*
gh run list --repo Cursiv-Local/Cursiv --workflow mac-build.yml --limit 2 --json databaseId,event,status
```

Cancel the run with `"event":"release"` (`gh run cancel <id>`); its upload step also
refuses to replace owner-signed assets. Confirm the published digests:

```bash
gh api repos/Cursiv-Local/Cursiv/releases/tags/v3.14-U96 -q '.assets[] | "\(.name) \(.digest)"'
```

## 8. Website and evidence (one PR), then deploy

On a branch from main, `scripts/website_release.py` makes the page and doc edits below in
one checked step (it stops before writing if any expected line is missing):

```bash
py -3.13 scripts/website_release.py --old U96 --new U97 --old-hash <U96 Windows SHA-256>   --new-hash <U97 Windows SHA-256> --old-windows <U96 count> --windows <U97 count>   --mac <Mac count> --mac-skips <Mac skips> --title "<short title>"   --summary "<Start page sentence>" --section "<test page paragraph>"
```

What it covers, for reference:

- `cp "$A/owner-release.json" website/assets/cursiv-owner-release-U96.json`
- Update the previous version to U96 in `README.md`, `TECH.md`, `docs/CLAIM-EVIDENCE.md`,
  `website/index.html`, `start.html` (download links, Mac link, current-release line,
  Windows SHA-256 and its element id, signed manifest link, `Get-FileHash` lines),
  `testers.html`, `vision.html`, and add a `<section id="u96">` to
  `website/ai-reliability-testing.html`.
- Add `docs/U96-RELEASE-VERIFICATION.md` (its "Full isolated Windows suite: **N passed, N skipped**"
  line is checked by the website tests), the docs index row and a HANDOFF note.

```bash
node cloudflare/publish.mjs --build-only
node --test cloudflare/tests/*.test.mjs
```

Open the PR, wait for checks, merge, then deploy from the merged main and check it live:

```bash
git switch main && git pull --ff-only
node cloudflare/publish.mjs
curl -sI https://cursiv.us/ | grep -i cache-control
```

Every page must send `no-transform`; the live HTML must equal `cloudflare/dist`, and the
downloaded installers must match the signed hashes.

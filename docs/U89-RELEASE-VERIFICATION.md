# U89 release verification

Application tag: `v3.14-U89` at
`e9828f605e7da08fdb3b59fe3d3bd198ddf4a177`.
U88 remains an unpublished candidate; its existing tag was not moved.

## Source gates

Full isolated Windows suite: **1,594 passed, 1 skipped**, 175.16 seconds,
Python 3.13 in the hash-locked release environment. Snapshot/log:
`%TEMP%/cursiv-live-followup-p7hf75qg`.

The U88 checkpoint also passed 1,594/1 locally, but its Mac isolation fixture
timed out in native reverse-DNS/proxy discovery. The corrected U89 fixture uses
a direct loopback server without proxy discovery; it retains all external socket,
DNS, HTTP and loopback assertions. Earlier parser and observer failures are
recorded in the engineering audit, not excluded from the suite.

The new targeted U89 run passed **66 tests**, including actual create/confirmed
append/read bytes, local search, source precedence, restricted actions, owner
manifest tampering, pre-execution revalidation and the independent OS observer.

Hosted source, package, asset-hash and publication outcomes are added below only
after execution completes. Security CI has passed; the locked dependency audit
reported no known vulnerabilities, and the high-severity/high-confidence Bandit
gate reported zero findings. Lower-priority findings remain separately documented.

## Owner authentication

Public owner-key fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.

The private key remains DPAPI-protected in the owner's Windows profile, outside
GitHub and OneDrive. Final installer hashes will be signed in `owner-release.json`
after the builds. The updater pins this public key and rechecks signed file
hashes before execution. A release hash alone is not identity authentication.
No Windows trust-store certificate was added. Windows-trusted Authenticode and
Mac notarization are still unavailable; owner signatures are detached proof.
The owner still needs an encrypted offline recovery backup of the key.

## Verification limits

No new full truth-benchmark score is claimed. The unchanged historical U85 run
passed **153/158** with documented misses; its safety failures were not removed.
Software regressions and native cryptographic/file checks are not a general
model-accuracy score. Clean-PC installation, installed upgrades and physical USB
memory persistence remain manual tests. The application-level network gate is
not an OS-wide firewall for arbitrary native code or external processes.

The pre-deployment public download counter returned 503 with `total:null`, as it
did before this release; it is not reported as zero downloads.

## Completed hosted and package checks

- Hosted source CI [39901889748](https://github.com/Cursiv-Local/Cursiv/actions/runs/39901889748)
  passed on the tagged application commit: **1,594 passed, 1 skipped on Windows**
  (155.74 s), **1,580 passed, 15 skipped on Mac** (380.97 s); security job passed.
- Mac package job [39901892601](https://github.com/Cursiv-Local/Cursiv/actions/runs/39901892601)
  checked out the same commit while it was on the feature branch; that exact
  commit is named by `v3.14-U89`. Its full suite passed **1,580/15**, 405.91 s,
  then the frozen app/notebook self-test passed, including the pinned owner key.
- Windows built in a clean detached tag worktree using the checked/hash-locked
  environment. PyInstaller, isolated frozen self-test and Inno Setup all passed.
- Both provenance files identify the exact application commit. Windows Python
  3.13.13 and Mac Python 3.13.16/tool versions are recorded. Platform checkout line
  endings can produce different raw lock-file hashes; package pins agree.
- The actual production Windows updater verifier and the Mac file verifier both
  returned `OwnerSignatureValid` for these final bytes. The owner signed eight
  binary/checksum/provenance assets locally; no signing key went to CI.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Windows versioned and stable installers | 55,995,637 each | `ea9768280e796b0a118ce85cfa5a7ccfbc7e268409615c2d27d7fa050b4e1351` |
| Mac versioned and stable DMGs | 68,853,954 each | `f5e97bd78d841175a9deef9d0b44a8c2a61d215faffb894777fd0df6b159a338` |

Windows PE signing status remains unsigned/unknown publisher; Mac is not
notarized. The detached owner signature authenticates the above hashes to the
pinned public key. No CA/SmartScreen trust claim is made.

The static site build and **21 website tests passed**, including independent
Node Ed25519 verification of the same owner manifest, public-key fingerprint,
displayed installer hash, version-specific download link, analytics privacy and
historical benchmark consistency. The initial website check correctly rejected
the retired moving `latest` URL expectation; the check now requires the exact
current owner-signed versioned installer URL. Stable aliases remain on GitHub
for existing clients and are covered by the same owner manifest.

## Publication and public verification

U89 is published as GitHub latest, not a draft/prerelease:
https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U89

Existing Cloudflare Worker `cursiv-web` deployed version
`0872910f-4065-483b-9ce0-0344dabe4894`; no DNS or hosting migration was performed.

All **38 anonymous public checks passed** at 2026-10-23 05:04:27 UTC:

- Latest stable tag resolves to the tested app commit.
- Public Windows/Mac stable binaries, versioned alias digests and checksum files
  agree with the independently verified owner signature, exact sizes and hashes.
- Website public key matches the app's pinned identity; its manifest matches
  GitHub's signed manifest and `/start` displays the actual Windows hash/fingerprint.
- HTTPS/canonical URLs, JSON-LD and indexability pass. Generated current HTML
  matches production after removing only the exact pre-existing Cloudflare beacon
  captured in the pre-deployment baseline, with line endings normalized.
- Tester contact/privacy headers, social image dimensions/absolute metadata,
  phone/app/notebook routes, robots, sitemap, health, anonymous admin rejection
  and the legacy hostname's permanent path-preserving redirect pass.

The existing public counter still reports 503/unavailable with `total:null`.
No counter repair or zero-download claim is made. Public verification evidence is
attached as `u89-release-verification.json`; raw checks are retained locally in
`cloudflare/.wrangler/u89-release-review/`.

Publishing triggered redundant Mac job `39903584651`; it was cancelled with its
release-upload step skipped. Existing owner-signed assets were not replaced.
Both main and the feature branch contain the reviewed changes; the app tag stays
immutable while later documentation commits record completed verification.

The owner’s installed desktop application was not replaced or restarted.
Personal `test_internals/u81_test.txt` retains SHA-256
`efb67cb4aa306cbe3daf6dafd432fa918fa91f7e21dd3278cdf2489b84e0cac7`.

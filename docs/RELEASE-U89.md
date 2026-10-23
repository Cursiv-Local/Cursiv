# Cursiv v3.14-U89 — workspace routing and owner release authentication

- Route natural workspace list/search/read/create/append requests to native tools.
  Local searches work offline and return paths and matching line numbers.
- Separate task language from file paths, keep source reads out of the notebook
  router, and expose bounded source summaries without a model continuation.
- Keep existing-file confirmation, workspace boundaries, credential denial and
  restricted-turn blocks. Compound file instructions run the first safe step
  and explicitly leave remaining steps unexecuted.
- Finish the previous live-transcript fixes: native flow/consumption/arrival math,
  phone import guidance, conservative verified forgetting, combined version/state
  and short application-owned denials. Retain actual source/calculation receipts.
- Authenticate installer bytes using a locally held owner release key and a
  public signed manifest. GitHub metadata and checksums alone cannot authorize an
  installer. Verify again before launching and remove partial failed downloads.
- Reject link/junction/hard-link/unsupported-object substitutions in signed
  notebook exports without changing stored notebook records or chains.
- Pin and hash release dependencies, record environment/artifact provenance, and
  add vulnerability/static checks to CI.

## Signing and remaining limits

These are owner-signed release manifests, not Windows-trusted Authenticode or Mac
notarization. Windows publisher warnings remain. No signing private key is stored
in GitHub, OneDrive, the website or installers. The owner still needs to make an
encrypted offline recovery backup. [Signing and recovery](OWNER-RELEASE-SIGNING.md).

Python network isolation remains an application boundary, not an OS firewall for
all native libraries, Ollama plugins or child processes. Clean-machine install,
physical USB memory persistence and recovery drills remain manual validation.
No new full local-model truth benchmark score is claimed.

Test, build, artifact-hash and publication outcomes are recorded only after they
complete in the U89 verification report.

## Completed release gates

- Windows: 1,594 tests passed, one platform skip. Mac: 1,580 passed, 15 skips.
- Both frozen app/notebook checks passed, including the bundled owner public key.
- All 21 website tests passed; dependency and high-severity static gates passed.
- Immutable application source: `e9828f605e7da08fdb3b59fe3d3bd198ddf4a177`.
- Windows installer SHA-256:
  `ea9768280e796b0a118ce85cfa5a7ccfbc7e268409615c2d27d7fa050b4e1351`.
- Mac DMG SHA-256:
  `f5e97bd78d841175a9deef9d0b44a8c2a61d215faffb894777fd0df6b159a338`.

Download `owner-release.json` with the installer: it authenticates the exact
binary/checksum/provenance files using the separately held owner key. The public
key and fingerprint are published with the release and on the download page.
U87 and earlier do not enforce this new signature: independently verify your
first U89 installer. Genuine U89 installs pin the key for subsequent updates.

[Full verification and limits](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/U89-RELEASE-VERIFICATION.md)
· [Owner key and recovery](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/OWNER-RELEASE-SIGNING.md).

U88 was an unpublished validation candidate. Its tag remains unchanged; U89
contains the corrected Mac fixture and all intended repairs.

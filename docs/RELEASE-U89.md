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

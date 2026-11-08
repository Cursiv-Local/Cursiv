# Cursiv v3.14-U119 — Robot evidence import

This release adds one feature: signed evidence from [Cursiv Robotics](https://github.com/Cursiv-Local/Cursiv-Robotics) can now
be verified, imported and written up in Cursiv. [User guide](ROBOT-EVIDENCE.md).

- **Import robot evidence.** Packages can come from robots, sensor stations, the phone importer (phyphox recordings) or the virtual
  lab, on a USB drive or in a folder.
  - `robot evidence find <folder>` shows what is there and how each package checks out. Nothing is imported yet.
  - `robot evidence import <folder>`, or Research → Research Files → **Import robot evidence…**, imports them.
  - Each package is checked by the independent verifier bundled with the app (`cursiv-verify`, built from a pinned Cursiv-Robotics
    commit). It is then copied byte for byte and checked again, and the drive is left untouched.
- **Trust is deliberate.** `robot trust add <trust.json>` shows exactly which keys would be trusted. They are saved only when you
  repeat the command with `confirm`. Keys inside packages are never trusted. A package signed by keys you haven't trusted is
  imported only if you type `without trust`, and it is then labelled "authenticity not assessed".
- **Answers cite records.** Each package's research summary goes into your documents, so answers cite individual records as
  `robot/observation_id`. Cursiv checks those citations: a record that isn't in any imported package is flagged under the answer.
- **"Fully verified" means every check passed.** That includes the science checks. Anything less is labelled NOT fully verified,
  with the reasons:
  - in import replies;
  - in `robot evidence`;
  - at the top of the package's summary;
  - under any answer that cites its records without saying so.
- **When nothing is imported.** Nothing is imported, and any partial copy is removed, if:
  - the drive changes during import;
  - the copy differs from what was verified;
  - records are missing;
  - the verifier does not finish in time (one hour by default; `CURSIV_VERIFY_TIMEOUT`).
- **Builds.** Release builds include the verifier and refuse to build without it. The self-test now checks that it is bundled and starts.

Validation: see the [release verification record](U119-RELEASE-VERIFICATION.md). Automated checks used mocked providers and
synthetic robot evidence packages only. There were no real AI calls, and no package from a real robot or sensor station was
imported. The new Research Files button has not been exercised by a person.

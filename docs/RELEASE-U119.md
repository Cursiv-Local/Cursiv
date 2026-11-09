# Cursiv v3.14-U119 — not published

The v3.14-U119 tag (`5184d4e`) was never published. Its Windows release build stopped before packaging.
`scripts/build_release.py` runs packaging with a trimmed PATH, which leaves out Rust's cargo, so the
robot evidence verifier could not be built. The macOS build passed.

Tags are not moved (as with U88), so the same feature ships in [U120](RELEASE-U120.md) with that fix.

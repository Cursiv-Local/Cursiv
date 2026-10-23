# U88 candidate — not published

The candidate tag `v3.14-U88` remains at `2de3f514c302eebbe370134a8b22bc3039f98b56`.
Windows passed 1,594 tests with one skip and its frozen installer compiled, but
the Mac network-isolation fixture hung in native reverse-DNS/proxy discovery.
The fixture was corrected without relaxing the network assertions.
No U88 GitHub release or website deployment was published. The final corrected
release is [U89](RELEASE-U89.md); the candidate tag was not rewritten.

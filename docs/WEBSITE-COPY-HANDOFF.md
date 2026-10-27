# Website copy cleanup handoff

Owner requested return to website, stop agent implementation, shorten every public page, remove old
GitHub links, and provide separate substantial crawlable reference pages for deeper product research.
Started October26,2026 from main a4cef6f6610d4981d26ec31aad2b57be5b5c9094.
Branch codex/website-clearer-copy. U107 has only two untracked planning documents; no runtime edits,
benchmarks or background commands were started. Leave those plans out of website commits.

## Work

Baseline public text inventory: ignored reports/website-copy-before.json. Homepage1030 words,
testing4539, local AI816, compare749, documentation494. Counts include closed detail text and omit
navigation/scripts/styles; they are reading-load proxies, not human usability measurements.

Short human-facing pages plus three substantive public references: local-AI capabilities, notebook
integrity/retrieval, portable/offline workspaces. Same content for crawlers and people, normal links,
canonical URLs, sitemap and experimental llms.txt. No keyword clones, hidden text or recommendation
instructions. Preserve privacy/signature/benchmark evidence and necessary warnings, use disclosure
for optional detail. Keep visual branding, downloads, application tools/private exclusions intact.

Do not read/modify excluded local paths, station code, owner data or secrets. No application release.
Next: edit copy/reference pages, build and existing website checks, desktop/mobile review, measure
before/after text and links, then finish the already-authorized website publication with production proof.

## Implemented and verified before publication

All17 existing public pages shortened or given concise disclosure navigation. Main-content counts
are in bench/results/website-copy-reading-load.json: homepage1030->284 total words (initial574->175),
local-AI816->150, compare749->199, guides494->120, setup898->360. Historical testing evidence and
full privacy disclosures remain available; testing initial4490->220, privacy initial1732->79.
Counts omit navigation/scripts; initial counts exclude closed bodies. Not a human usability study.

Three public reference pages preserve deeper material: local-ai-reference857 words,
notebook-reference661, portable-ai-reference651. All are ordinary static HTML for every visitor,
linked from guides and llms.txt, self-canonical and included in the expanded20-entry sitemap.
Zero former GitHub-account links remain in website/. Checked391 local/source links without failures.
Fixed the obsolete setup encryption FAQ and corrected the vision page's platform-skip wording.

31 website checks and6 aggregate-measurement tests passed. Updated existing discovery checks to
follow moved technical detail and match actual private path boundaries (not confuse notebook-reference
with private /notebook). Desktop/default1280 and explicit390 mobile reviews covered all20 public
pages; no horizontal overflow. Mobile menu opened/closed; viewport reset. A screenshot aspect-ratio
issue found during review was fixed. Evidence: bench/results/website-copy-layout.json.

Source integration proceeds through normal commit/PR checks. Production verification is next; only
allowlisted public files are published. Preview server session87942 on loopback8768 is currently
running and must stop after live proof. Applied one-off rewrite scripts in ignored reports/ must
not be rerun. Existing U107 plans stay untracked and outside website commits.

## Publication complete

Source4cbb36dcf42112a4776979f228372334156e0649, Cloudflare version
ae94cf83-ed22-44df-abdf-6ea8b5f4fd41. Commit USB gate45/45 passed before publishing.
Production49 public probes:48 final200 and the intentional removed /letters404; zero failures.
All20 canonical/indexable sitemap pages match deployed source bytes; source-history lastmod present.
Nine additional reference probes (three pages x Googlebot/OpenAI-search/Claude-search user-agent
strings) all returned200 and identical browser-content hashes. These are access tests, not proof of
verified crawler identity, indexing or recommendations. No recommendation/ranking gain claimed.
Icons, signed release metadata, private exclusions and U106 immutable tag remain unchanged.

Public receipts: bench/results/website-copy-live.json and website-copy-publication.json.
Actual live screenshot: bench/results/website-copy-live-home.jpg. Local preview sessions1516,
91797 and87942 have stopped; no preview server remains. All publication commands finished.
Normal source/website PR checks govern source integration; consult repository PR status before
continuing. No further website implementation or deployment is required. U107 agent work remains
unstarted beyond its untracked planning notes, per the owner's direction back to the website.

This organization follows Google's ordinary crawlable-content/internal-link guidance. Detailed
reference pages serve the same HTML to all readers; no hidden bot-only version is used:
https://developers.google.com/search/docs/appearance/ai-features
https://developers.google.com/search/docs/essentials/spam-policies

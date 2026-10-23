# Field kit test: Cursiv on an SSD

**2026-10-22 owner update:** basic physical USB operation works in the owner's
testing. USB memory saves, persistence after restart and cross-machine retrieval
remain untested; the owner has access to a second clean Windows PC. Start with
[the focused persistence check](USB-PERSISTENCE-CHECK.md). Automated portable
regressions are separate from physical evidence. No second-PC/full-day result
was established by this task. Do not interpret unchecked steps as passes. Record the actual
release, devices, drive and failures when the kit is available; use disposable
observations for the deliberate failure tests.

The checklist for research roadmap R5: show that a Cursiv drive works on laptops it has never
seen, all day, with no internet. Do it before telling a research group the kit is ready.
Write down what actually happened, including what failed; the result goes in
`docs/HARDWARE.md` and nothing is claimed that wasn't tested.

## What you need

- A USB 3 SSD (or a fast 64 GB+ USB drive), formatted **exFAT**.
- Two Windows laptops that have **never had Cursiv or Ollama installed**. One with a graphics
  card if possible, one without (processor only is what most field laptops get).
- A charged battery on each, a watch or phone for times, and this page printed.

## 1. Make the drive

- [ ] On the build computer: tray menu → **Make a Cursiv USB…**, "start fresh" (no memories or keys).
- [ ] Note the actual release/tag, the drive's size and free space after copying.
- [ ] Safely eject the drive.

## 2. First laptop, no internet

- [ ] Turn Wi-Fi off and unplug any network cable **before** plugging in the drive.
- [ ] Double-click **Start Cursiv**. Time from double-click to the chat being ready: ____ s.
- [ ] Nothing asked to install, nothing asked for administrator rights.
- [ ] Type `status`: it says offline mode is on.
- [ ] Ask "Are you offline right now?": the answer matches the real state.
- [ ] Ask a first-aid question ("my coworker cut his arm and it's bleeding badly"): the answer
      quotes the reference and says to call 911.
- [ ] `log site: Test site; water temp 12.40 C; pH 7.2; 44.1234, -71.5678; note: kit test` saves,
      and `field log check` says all entries are intact.
- [ ] Import a PDF protocol in **Your documents**, ask about it: the answer quotes the page.
- [ ] Field calculation: "What is 44.1234, -71.5678 in UTM?" gives zone 19, about 294554 E.
- [ ] Time three ordinary answers (about a paragraph each): ____ s, ____ s, ____ s.
- [ ] Close Cursiv. Confirm Cursiv-managed saved data is on the drive and record
      any host files separately. Windows and an existing host Ollama service can
      retain their own traces; portability is not a guarantee of zero host traces.

## 3. Second laptop

- [ ] Repeat section 2 on the other laptop with the same drive.
- [ ] The field entry from laptop 1 is still there; `field log check` still says intact.

## 4. A full day on battery

- [ ] Laptop unplugged, battery saver on (Settings → Battery saver).
- [ ] Start time and battery %: ________. Use it as a field day would: a few entries and
      questions an hour.
- [ ] Every hour: battery %, and whether answers still come back. Time at which the battery
      reached 10%: ________.

## 5. Things going wrong

- [ ] **Pull the drive out while Cursiv is open** (after saving an entry). Plug it back in,
      start again: the log opens, `field log check` reports either intact or exactly one
      incomplete last line, never silent damage.
- [ ] **Power cut:** hold the power button while an entry is being saved. Same check.
- [ ] **Full drive:** fill the drive to a few MB free with a large file. Saving an entry says
      it couldn't be saved; nothing earlier is lost. Delete the file afterwards.
- [ ] **Team sync:** on each laptop log two entries, then **Share with team…** to a second USB
      stick; on each, **Import from team…**. `team log` shows every entry once, from both laptops.

## 6. Record the result

- [ ] Add a "Field kit test" section to `docs/HARDWARE.md`: date, release, the two laptops
      (processor, memory, graphics), the times, the battery hours, and every failure.
- [ ] Anything that failed becomes an issue before the kit is offered to anyone.

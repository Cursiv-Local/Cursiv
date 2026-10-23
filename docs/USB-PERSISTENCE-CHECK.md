# Focused USB persistence check

**Owner report, 2026-10-22:** basic physical USB operation works. Saving and
retrieving memories on that USB has not yet been tested. This checklist is
uncompleted until actual results are recorded. A second clean Windows PC is
available to the owner, not connected to this execution session.

Use a backed-up kit and clearly marked disposable records. Do this outside demo
mode, using the same Cursiv account on both PCs. Record the actual kit version,
drive label, computer and observed paths; source tests do not establish that a
previously made USB contains the latest source changes.

## 1. Confirm the portable copy

- [ ] Start Cursiv from the USB, then `demo off`, `offline on`, `status`, and
  `presence status`. Record the actual version and confirm `portable: true`.
- [ ] Confirm the authorized workspace is on that USB. If necessary choose its
  Workspace folder with `workspace <actual folder>` and enable `files on`.
- [ ] Current portable layout uses `<USB>\Home\.cursiv` for Cursiv-managed data.
  If an older kit differs, record what it actually uses; do not manually move
  existing memory stores or infer that an installer directory is the data home.

## 2. Save three independently recognizable markers

Choose fresh marker strings if these were used before. In Cursiv:

```text
remember My USB persistence marker is USB-PERSIST-4821.
log site: USB persistence test; sample ID: USB-4821; note: Disposable persistence check
file create usb-persistence-4821.txt :: USB-FILE-4821
```

- [ ] Record the confirmed memory ID, notebook ID/fingerprint and exact absolute
  file destination. A model saying “saved” is not enough.
- [ ] Run `field log check`, then `field log sample USB-4821`.
- [ ] Close Cursiv completely, including the system-tray process, before ejecting.

## 3. Verify actual bytes on the USB

After closing Cursiv, replace `E:\` with the actual USB root. These PowerShell
commands only read files:

```powershell
$kitRoot = 'E:\'
$kitData = Join-Path $kitRoot 'Home\.cursiv'
Select-String -LiteralPath (Join-Path $kitData 'memory_facts.jsonl') -SimpleMatch 'USB-PERSIST-4821'
Select-String -LiteralPath (Join-Path $kitData 'fieldlog\observations.jsonl') -SimpleMatch 'USB-4821'
Get-Content -LiteralPath (Join-Path $kitRoot 'Workspace\usb-persistence-4821.txt')
```

Use the actual workspace path if it differs. If a file or marker is absent,
record a failure and the reported path. Do not treat a remembered model answer
as proof that the file exists on the drive. Presence of a marker proves these
specific bytes persisted; it does not certify every memory/retrieval operation.

## 4. Restart, then change computers

- [ ] Reopen the USB copy on the first PC. Read
  `file read usb-persistence-4821.txt`, inspect `field log sample USB-4821`, and
  run `field log check`. Verify the same IDs, fingerprint and exact file marker.
- [ ] Look up `USB-PERSIST-4821` in Saved Notes or ask for that saved fact.
  Record retrieval separately from the independent byte check: a failed recall
  can be a retrieval problem even when the stored record exists.
- [ ] Close/eject safely, move the same kit to the second clean PC with network
  access disabled, start from the USB and confirm `portable: true` again.
- [ ] Repeat the three reads/checks. If the drive letter changed, record the new
  absolute file path and verify the same underlying USB records are used.

| Check | Actual version/device/path | Pass/fail and evidence |
|---|---|---|
| Basic USB operation | Owner reported working; device/version unspecified | Owner report only |
| Memory marker exists on USB | | Not tested |
| Workspace file persists after restart | | Not tested |
| Notebook ID/chain survives restart | | Not tested |
| Memory retrieval after restart | | Not tested |
| Same records on second clean PC | | Not tested |

Keep or clearly label these disposable test records; this guide does not delete
existing files or rewrite the append-only notebook. The longer
[field-kit checklist](FIELD-KIT-TEST.md) still covers battery life, full-drive,
disconnect, recovery and independent field use.

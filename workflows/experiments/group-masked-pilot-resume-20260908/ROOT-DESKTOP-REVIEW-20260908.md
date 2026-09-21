# Current desktop lifetimes — bounded root review

At 05:53Z the original capture found 20 surviving, previously reviewed desktop
lifetimes, but NVML also listed two new desktop lifetimes. No GPU or process was
stopped, adopted by name, or removed from monitoring. Production workers 52720
and19552 and their trampolines remain the original ones; both queues were empty.

The separate read-only `desktop-parent-evidence-20260908.json` records the exact
four CIM process rows at05:56:31Z, including full argv where available:

- WUDFHost39712 was created05:43:16.240631Z by the existing protected
  services.exe2012. Its executable/argv remain inaccessible (null), not guessed.
  This is consistent with the Windows user-mode driver host. Root accepts this
  exact parent/name/PID/creation lifetime with explicit protected-null review,
  not a claim that its inaccessible executable bytes were verified.
- AMDRSSrcExt54788 was created05:43:18.926518Z by AMDRSServ14796, whose full
  WindowsApps AMD package executable/argv were read. The child's executable
  Authenticode signature was Valid, signed by Advanced Micro Devices. Its exact
  argv identifies the AMD DVR overlay. Root accepts only this captured lifetime,
  executable and complete argv, not future AMD processes by name.

Neither is an exact match to the prior process lifetime. The historical candidate
and its `matches_prior_lifetime` facts must remain unchanged. A fresh supplemental
candidate, hash-bound time-limited approval, and exact-field live comparison are
required before either new PID may be admitted. Any unexpected GPU-listed PID,
PID reuse, changed creation/parent/executable/argv or expired approval must refuse.

This review does not lower memory/GPU thresholds, skip queue checks, authorize
closing other applications, change the frozen image graph or grant general GPU
process exceptions. It is limited to the one previously requested local Group
pilot. No new prompt had been submitted when this review was written.

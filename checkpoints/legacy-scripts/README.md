# Legacy experiment tooling

This directory preserves launchers, builders, templates, and lock files for rejected or superseded
experiments. They are kept outside the live `scripts`, `config`, and `templates` trees so routine work
does not mistake them for supported production tooling.

The archived files retain their original path assumptions for forensic comparison. To reproduce an
old experiment, first copy its scripts back to `scripts`, its YAML/lock files back to `config`, and the
HiDream source templates back to the currently absent *templates\hidream-o1* destination, then follow the
matching evaluation document.
Do not run archived launchers in place.

The selected FLUX.2 Dev V2, Klein 4B V1/V3, and Klein 9B V3 training and validation helpers remain in
the live trees. Some of those helpers have older version names because the selected V3 chain reuses
them; they are intentionally not archived.

The `flux2-klein9b-v1`, `v2`, `v4`, `v5`, and `v6` folders contain only version-specific wrappers,
configs, and planning tools for non-selected runs. Shared helpers still required by the selected V3
chain remain under `scripts` and `config` even when an older version appears in their filename.

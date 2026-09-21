# Shape and restoration composition — isolated CPU test

The prior turn supplied useful negative evidence:115-control source geometry
changes projected facial proportions while preserving the detailed scene, but
leaves tense crease/skin texture. Existing CodeFormer0.7 separately cleans
texture but did not restore source-like proportions. Neither is a complete High.

This test asks whether their **composition** is useful. It does not reopen the
closed shape-strength, landmark-density or CodeFormer-weight sweeps. One frozen
input, the previously reviewed safe shape result, enters the already-installed
CodeFormer at0.7. No Low smoothing/forced smile/cheek highlights are applied before
restoration. Alignment is re-detected on the edited face as required by the
existing per-image alignment policy, not frozen to a differently shaped face.

## Conditioning and compatibility

- Input: `whole-face-shape-house-feature-cage/candidate.png`, SHA
  8359B7CCD65B113D3767AE2B18B34E64CCA41143E53135BB580AE550B82E841B.
- Parent audit SHA118B5AB9850C70BF1F62AE6C6C8CEC93E1BCB8878D05B38E69E6D435B3303791.
  The input contains native Klein9B V3-LoRA identity texture and source-guided
  2D geometry. It is synthetic and never counted as a genuine scoring anchor.
- CodeFormer receives512px aligned RGB only, with no genuine-photo input or
  face embedding. This is learned restoration, **not identity conditioning**.
- Same local checkpoint SHA1009E537E0C2A07D4CABCE6355F53CB66767CD4B4297EC7A4A64CA4B8A5684B7;
  params_ema,512embedding/1024codebook/8heads/9layers, AdaINtrue, weight0.7, CPU.
- [Author inference](https://raw.githubusercontent.com/sczhou/CodeFormer/master/inference_codeformer.py)
  and [README](https://github.com/sczhou/CodeFormer#testing) rechecked2026-09-04.
  Existing local SCRFD substitution supplies five-point FFHQ alignment.
- If the aligned crop is useful, assemble through the inspected installed
  ReActor FaceRestoreHelper at1x with existing ParseNet. Constructor is bypassed
  to prevent downloads. No upsampler, no new mask recipe, no GPU queue or cache
  change, no source texture transplant, no public workflow change.

Identity prediction is limited: the decoder can improve coarse texture but can
change features. Six genuine EXIF-oriented held-out photos measure that tradeoff.
Similarity is a diagnostic, not an attractiveness score or pass/fail by itself.

## Acceptance

A visibly more appealing recognizable face than actual Low: clearer attractive
eyes/brows and source-like closed expression, without round puffy cheeks, waxy
skin, false teeth, hairline artifacts or lost background detail. Inspect aligned
input/restoration, then full size and thumbnail if assembled. Source gaze and
pose must be measured; do not call uncorrected restoration an exact gaze lock.

If texture improves but expression is still unflattering, the combination fails
the High objective. Do not expand to a three-photo/public trial or make another
weight/geometry refinement merely to obtain a passing diagnostic.

## Outcome: rejected; no production promotion

The aligned house preview was sufficiently cleaner to inspect at full frame,
but that frame is too soft/airbrushed against the sharp clothing and background.
Brows weaken; the mouth remains comparatively neutral rather than the preferred
source expression. Hair retains bundled strands. Closed lips, source-like pose,
and detailed background survive, with no conspicuous new head halo. This is a
visible change, but not the stronger, realistic High requested by Mitch.

The final frozen composition was also run on the existing canyon and genuine
third raw files to check generalization. This exceeded the original conditional
stop in the plan above: record it as an additional CPU failure diagnosis, not
as an accepted house result or three-photo success. Neither case passed the
geometry safety guard; neither reached restoration or emitted a candidate.
No per-photo strength reduction or further cage/weight sweep was attempted.

| Frozen case | Result | Diagnostic |
| --- | --- | --- |
| House | Full candidate reviewed; rejected visually | Likeness 0.629029; CPU Low 0.737938 |
| Canyon | Aborted before restoration | Minimum inverse Jacobian -0.6406 |
| Genuine third | Aborted before restoration | Minimum inverse Jacobian -0.5143 |

All three use the historical four-reference native policy. The third deliberately
uses `third-baseline-native/raw_00001_.png`, not the more favorable source-only
parent. That raw already has pose/mouth errors; the failed composition does not
repair them. No independently rerun diffusion graph is claimed.

House final gaze correction gives source-pose error 0.684497 degrees and mouth
opening ratio 0.003842. Its strict five-photo likeness (also excluding the
hair-conditioning photograph) is 0.624841. The third's genuine source original
was excluded from its reference list before processing. All genuine JPGs use
EXIF-corrected orientation. Scores measure recognition, not attractiveness.
Rejection is not based solely on falling below 0.70.

House exterior pixels beyond the 64px head margin differ by at most 2/255,
mean 0.029372/255; do not call the restored background pixel-identical. The
pre-final-gaze replay differs by at most 1/255 from the earlier full-frame
assembly, so that replay is not pixel-identical either.

### Preserved evidence

Paths below are relative to `work/upgrade-source-faithful-20260903`:

- `shape-codeformer-house-aligned/audit.json`: SHA
  B76F10750F664E5D1DC6BA608B1D1D4F1AD7D056969034FA1EB70DB6F7E0B964.
  The restored aligned crop was not detected by the scoring detector; this is
  not a final full-frame detection failure.
- `shape-codeformer-house-full-frame/audit.json`: SHA
  5ED4E6E26E57B98B6EDCB3C88338E582254CE5D704FA5BA29D0898F18EB783A8;
  full-frame likeness 0.629595 before final gaze correction.
- `shape-restoration-policy-house/audit.json`: SHA
  054D744559D58B3A969899667B9B5A674EBB3683CC19E67A0085CF44759F387E;
  final candidate SHA
  0A9C341F8A81D645A21FAE54D84384903B9350A1248760D0237BA79187D600C9.
- `shape-restoration-policy-canyon/failure.json`: SHA
  5B2E5F57F74894E4D32AE52E61D632540AA4066B199ADE1A1695F545FFFED80E.
- `shape-restoration-policy-third/failure.json`: SHA
  7938EB256DCC3E956A837315A53EF7E3D9F3974D10D0A219560D9889E06444A7.

The house audit status `three_case_policy_component_evaluated_not_promoted`
names the shared test policy, not three successful results. This outcome and
the two failure records take precedence over that overly broad status label.
Original audits and failed outputs are preserved without rewriting.

The composition route is closed. Production Low, High and main node remain
unchanged, Phone stays ON and Turbo OFF. No GPU work or cache release was needed.

## Verification

- EXIF-orientation regression passes for all six evaluation scripts, including
  the new shared-policy runner (one test with per-script/orientation subtests).
- Six existing whole-face geometry safety tests pass.
- The three experiment scripts and updated regression test compile.
- `git diff --check` passes; only existing LF/CRLF normalization warnings appear.
- Fresh SHA256 checks match the protected Low, main-node and High hashes, plus
  the three saved case audits/failure records above.

These checks validate bookkeeping and safety behavior, not image attractiveness.

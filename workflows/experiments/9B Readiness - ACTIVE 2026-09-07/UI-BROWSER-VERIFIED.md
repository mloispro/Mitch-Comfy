# Actual ComfyUI import/export verification — September8

Root imported these three exact experiment JSON files through the local8188
ComfyUI frontend using a separate temporary browser tab. No Run button, Save,
production edit or generation was invoked. Existing user workflow tabs were
left intact. The temporary browser tab was closed after verification.

The frontend showed the imported graphs and actual reference previews, without
a missing-node dialog. Each imported workflow was exported with the frontend's
Export(API) action under a unique filename. Root compared every execution node
against the corresponding frozen, actually executed payload using the existing
strict JSON comparator. Only presentation `_meta` titles were excluded; types,
input values, link order, model/reference choices and fixed seeds were retained.

| File | Exact execution nodes | Browser API export SHA256 |
| --- | ---: | --- |
| Solo Raw Examples / Solo - Rooftop Cocktail - PASSED SINGLE CASE - EXPERIMENT.json | 31 | 138081D138E1C42EC4981879143A0A7B2B7447169719A31A11BDD569C21BA20F |
| Upgrade Preserve Genuine Source / Upgrade - Preserve Genuine Source - EXPERIMENT.json | 20 | EC397FAA9C833599C176439ABFF85D2958CAEAC3AB1D0A0F412EF6442B0D84FC |
| Upgrade Preserve Genuine Source / Upgrade - Preserve Genuine Source - TURBO8 EXPERIMENT.json | 21 | A8A32903BBAB54FE7B2762A8A9D5B3AEBC1CE75D617DC014929B58C5EFD1C216 |

The three uniquely named exports remain in `C:/Users/Mitch/Downloads/`:
`codex-cocktail-ui-api-parity-20260908-0544.json`,
`codex-upgrade-quality-ui-api-parity-20260908-0547.json`, and
`codex-upgrade-turbo-ui-api-parity-20260908-0547.json`. No existing file was
overwritten. The browser download event timed out for the first export, but
the actual9353-byte file was present and its exact31-node comparison passed.
The other two files are5523 and5824bytes, respectively.

This later verification supersedes only the earlier *not yet browser tested*
status in immutable preparation/readme receipts. Those records are not rewritten.
It does not create new image passes, remove ordinary-node GPU safety requirements,
prove arbitrary inputs, or change the failed public cocktail conclusion.

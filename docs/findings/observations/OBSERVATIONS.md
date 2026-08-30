# Observations: GMI Cloud think time vs hop traces

Run `20260830T000722Z`. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob, not tool-call spans and not an agent loop. No winner rank.

GMI Cloud mean think_s is 17.1s (rank 2 of 4). Mean hops 12.0 (rank 2). Mean chars/hop 231 (rank 2). Mean reasoning_tokens 694 (rank 2). Mean tokens/hop 52 (rank 3). Longer think is not more hops. deepinfra has more mean hops (14.1 vs 12.0). GMI’s extra wall time lines up with think_s and reasoning_tokens, not with a uniquely high hop count.

Fail modes are a fold over hop lists plus trial quality. Gold solution text is not a classifier input. Across 108 trials: apply_fail 10, overthink 31, pass 57, short_wrong 10. `pass` is shown plus held-out pytest. `apply_fail` is a unified diff that did not apply. `overthink` is a fail with hop_count ≥ 8 or the same first-six-word stem on ≥ 3 hops. `short_wrong` is a fail with a short CoT that still missed the grade. deepinfra overthink 9 apply_fail 3 short_wrong 1; gmicloud overthink 9 apply_fail 2 short_wrong 1; novita overthink 8 apply_fail 3 short_wrong 3; z-ai overthink 5 apply_fail 2 short_wrong 5.

## Host hop size

| provider | n | pass | mean hops | mean chars/hop | mean chars | mean reason_tok | mean tokens/hop | mean think_s | reason tok / think_s | mean latency_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepinfra | 27 | 14/27 | 14.1 | 215 | 3498 | 897 | 55 | 17.6 | 52.8 | 30.9 |
| gmicloud | 27 | 15/27 | 12.0 | 231 | 3104 | 694 | 52 | 17.1 | 50.1 | 32.7 |
| novita | 27 | 13/27 | 7.6 | 243 | 2081 | 500 | 55 | 12.8 | 42.7 | 30.5 |
| z-ai | 27 | 15/27 | 11.6 | 212 | 2955 | 656 | 48 | 14.8 | 42.5 | 28.4 |

## Task complexity

Catalog marks every variance task `very_hard`. Empirical pass rate on this run splits them. Solved (4): `watermark_poison` 0.92, `entity_reload` 1.00, `read_write_split` 0.92, `drop_resurrect` 1.00. Mixed (2): `mtime_skip` 0.75, `field_readd` 0.17. Trip (3): `frozen_basis` 0.00, `rebuild_wipe` 0.00, `late_event_close` 0.00. Where they do well, CoT stays short (mean hops 3.3, think 3.1s). They name the bug and emit a small diff. Where they trip by overthinking: `frozen_basis` hops 23.3 think 29.3s, `rebuild_wipe` hops 10.8 think 15.6s, `late_event_close` hops 44.5 think 64.9s. Fail mode `overthink` is hop_count ≥ 8 or restated diagnosis, not extra tool hops. The longest think pile-up is `late_event_close` (64.9s, hops 44.5). Mixed but mostly apply-fail: `field_readd` 10/12 apply-fail, hops 3.0. Diagnosis is short. The patch does not land.

| task | catalog | empirical | band | pass | mean hops | hops on pass | hops on fail | mean think_s | fail modes | mechanism |
|---|---|---:|---|---:|---:|---:|---:|---:|---|---|
| `watermark_poison` | very_hard | 0.92 | solved | 11/12 | 4.1 | 4.5 | 0.0 | 3.9 | pass:11, short_wrong:1 | Watermark advances before the window commits. |
| `entity_reload` | very_hard | 1.00 | solved | 12/12 | 4.2 | 4.2 |  | 3.7 | pass:12 | Watermark picks changed keys; scan has no time predicate. |
| `frozen_basis` | very_hard | 0.00 | trip | 0/12 | 23.3 |  | 23.3 | 29.3 | overthink:12 | Chunk unique()s against a start-of-run snapshot with no existing rows. |
| `read_write_split` | very_hard | 0.92 | solved | 11/12 | 1.4 | 1.5 | 0.0 | 1.6 | pass:11, short_wrong:1 | Partitioned overwrite; the read still walks the full bronze tree. |
| `mtime_skip` | very_hard | 0.75 | mixed | 9/12 | 7.0 | 7.3 | 6.0 | 12.8 | overthink:1, pass:9, short_wrong:2 | Crash mid-chunk; output mtime treats unread older files as consumed. |
| `rebuild_wipe` | very_hard | 0.00 | trip | 0/12 | 10.8 |  | 10.8 | 15.6 | overthink:7, short_wrong:5 | Rebuild retry wipes staging checkpoints and restarts at record one. |
| `drop_resurrect` | very_hard | 1.00 | solved | 12/12 | 3.4 | 3.4 |  | 3.0 | pass:12 | Catalog drop; next writer get_or_create recreates the table. |
| `field_readd` | very_hard | 0.17 | mixed | 2/12 | 3.0 | 3.0 | 3.0 | 3.8 | apply_fail:10, pass:2 | Drop then re-add the same column name; old field identity is reused. |
| `late_event_close` | very_hard | 0.00 | trip | 0/12 | 44.5 |  | 44.5 | 64.9 | overthink:11, short_wrong:1 | Processing-time close marks the event-time window done; late facts vanish. |

## How to read this

More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger. Tokens per hop is `reasoning_tokens / hop_count`. Think_s is stream time spent in the reasoning phase. A host can think longer by writing bigger hops, more hops, or by emitting more tokens inside similar hop counts. Catalog `very_hard` does not predict hop load. Failures split by mode, not by host rank.

See [Findings 2](../2/FINDINGS.html) for pass/quality and TPS on the same rows. Findings 1 (an earlier four-host mix) had GMI mean latency 58.7s and mean reason_tok 2033. This hop-traced run does not repeat that gap. GMI still has the highest latency here, but mean think_s sits next to deepinfra. Shared instructions now ask for one claim then one diff; a later spend on that prompt is a new campaign vs this run.

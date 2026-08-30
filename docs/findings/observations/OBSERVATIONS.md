# Observations: GMI Cloud think time vs hop traces

Run `20260830T000722Z`. One-shot CoT. Hops are paragraph/claim cuts of the reasoning blob, not tool-call spans and not an agent loop. No winner rank.

GMI Cloud mean think_s is 17.1s (rank 2 of 4). Mean hops 12.0 (rank 2). Mean chars/hop 231 (rank 2). Mean reasoning_tokens 694 (rank 2). Mean tokens/hop 52 (rank 3). Longer think is not more hops. deepinfra has more mean hops (14.1 vs 12.0). GMI’s extra wall time lines up with think_s and reasoning_tokens, not with a uniquely high hop count.

## Host hop size

| provider | n | pass | mean hops | mean chars/hop | mean chars | mean reason_tok | mean tokens/hop | mean think_s | reason tok / think_s | mean latency_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepinfra | 27 | 14/27 | 14.1 | 215 | 3498 | 897 | 55 | 17.6 | 52.8 | 30.9 |
| gmicloud | 27 | 15/27 | 12.0 | 231 | 3104 | 694 | 52 | 17.1 | 50.1 | 32.7 |
| novita | 27 | 13/27 | 7.6 | 243 | 2081 | 500 | 55 | 12.8 | 42.7 | 30.5 |
| z-ai | 27 | 15/27 | 11.6 | 212 | 2955 | 656 | 48 | 14.8 | 42.5 | 28.4 |

## How to read this

More hops means the CoT broke into more claim/paragraph units. Longer hops means each unit is bigger. Tokens per hop is `reasoning_tokens / hop_count`. Think_s is stream time spent in the reasoning phase. A host can think longer by writing bigger hops, more hops, or by emitting more tokens inside similar hop counts.

See [Findings 2](../2/FINDINGS.html) for pass/quality and TPS on the same rows. Findings 1 (an earlier four-host mix) had GMI mean latency 58.7s and mean reason_tok 2033. This hop-traced run does not repeat that gap. GMI still has the highest latency here, but mean think_s sits next to deepinfra.

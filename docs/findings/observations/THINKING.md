# How overthink hops work

Run `20260830T042145Z`, k=5, four hosts, 177 trials with CoT. Hops are paragraph cuts of one-shot reasoning, not tool calls. PCA of hop TF-IDF (22% of variance in two components). No winner rank.

Hosts start on the **same first claim** for a given task. Overthink is not a new diagnosis. It is a revision loop: wait / actually / hmm, then another phrasing of the same window-vs-lateness (or empty-snapshot) fight, then a patch that still misses. Easy tasks exit after 2-4 hops. Hardware changes how long that loop runs, not which cloud the CoT sits in.

Open the [HTML](THINKING.html) for the cluster scatter and small multiples.

## Shared vs host

Solved tasks share a first-six-word stem on 18-20/20 trials (`drop_resurrect`, `watermark_poison`, `read_write_split`). `field_readd` first-hop Jaccard is 0.78 (same diagnosis, apply-fail). Hard tasks split the opening: `late_event_close` majority stem 7/20, Jaccard ~0.46.

Content PCA clusters by task. Host share of each cluster is interchangeable (~0.22-0.33). Overthink hops are 23% revision-marked vs 6% on pass. Unique-stem ratio stays ~0.96: they paraphrase, they do not paste the same sentence.

Once the loop starts, hop count is the host knob: novita overthink mean 35 hops / 56s think; DeepInfra 12 / 20s; GMI 18 / 20s; z-ai 21 / 32s. Novita keeps revising in the last quartile (0.32). z-ai cools off (0.13). Think TPS stays ~37-53 tok/s.

## Implications

Pass@k will not move by picking the deeper thinker. The four hosts already share the diagnosis cluster. GMI's long wall is a tail of the same loop Novita also runs, not a slower decoder. DeepInfra's edge here is exiting earlier, which also means more `short_wrong`. Next leverage is task-shaped (event-time close, empty-snapshot unique), not host-shaped.

# Provider variance 20260829T224943Z + 20260829T230214Z

Model `z-ai/glm-5.3-flash`  k=`3`  comparable=`True`  sha `ee28e391fdfc2194627367be89fd11a355c3fa48 0f1aa9d5ad2cbd7e92cf011669dca2a864f84907`  n=`108`  spend~$0.0405.

This eval is one-shot. The model returns one unified diff. There are no tool calls, no agent loop, and no hop-span traces. Reasoning efficiency here is `reasoning_tokens` vs `completion_tokens`, plus applied-diff identity, not search hops.

Do not read a winner rank out of these rates. k is small. Several tasks stay red on both hosts.

## Host totals

| provider | pass | rate | gold | equivalent | broken | format | infra | cost sum | mean reason_tok | mean completion | reason/completion | mean cached | cached>0 | mean latency_s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| novita | 13/27 | 0.481 | 5 | 8 | 10 | 0 | 2 | 0.0055 | 261.9 | 790.5 | 0.302 | 143.4 | 7 | 21.2 |
| z-ai | 17/27 | 0.630 | 8 | 9 | 9 | 0 | 0 | 0.0089 | 721.1 | 1281.3 | 0.362 | 384.0 | 27 | 25.7 |
| deepinfra | 17/27 | 0.630 | 7 | 10 | 8 | 0 | 0 | 0.0077 | 498.6 | 1017.7 | 0.375 | 0.0 | 0 | 24.3 |
| gmicloud | 16/27 | 0.593 | 3 | 13 | 8 | 0 | 0 | 0.0184 | 2033.2 | 2605.2 | 0.397 | 37.9 | 2 | 58.7 |

## Per task / trial

| task | trial | novita | z-ai | deepinfra | gmicloud |
|---|---|---|---|---|---|
| watermark_poison | 1 | PASS/gold | PASS/gold | PASS/gold | PASS/equivalent |
| watermark_poison | 2 | FAIL/ | PASS/gold | PASS/equivalent | PASS/gold |
| watermark_poison | 3 | PASS/gold | PASS/gold | PASS/gold | PASS/equivalent |
| entity_reload | 1 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| entity_reload | 2 | PASS/equivalent | PASS/gold | PASS/gold | PASS/equivalent |
| entity_reload | 3 | FAIL/ | PASS/gold | PASS/gold | PASS/equivalent |
| frozen_basis | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| frozen_basis | 2 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| frozen_basis | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| read_write_split | 1 | PASS/gold | PASS/gold | PASS/gold | PASS/gold |
| read_write_split | 2 | PASS/gold | PASS/gold | PASS/gold | PASS/gold |
| read_write_split | 3 | PASS/gold | PASS/gold | PASS/gold | PASS/equivalent |
| mtime_skip | 1 | FAIL/broken | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| mtime_skip | 2 | FAIL/broken | PASS/equivalent | FAIL/broken | PASS/equivalent |
| mtime_skip | 3 | PASS/equivalent | PASS/equivalent | PASS/equivalent | FAIL/broken |
| rebuild_wipe | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| rebuild_wipe | 2 | PASS/equivalent | FAIL/broken | PASS/equivalent | PASS/equivalent |
| rebuild_wipe | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| drop_resurrect | 1 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| drop_resurrect | 2 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| drop_resurrect | 3 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| field_readd | 1 | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply | PASS/equivalent | FAIL/patch_did_not_apply |
| field_readd | 2 | FAIL/patch_did_not_apply | PASS/equivalent | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply |
| field_readd | 3 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| late_event_close | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/patch_did_not_apply |
| late_event_close | 2 | FAIL/broken | FAIL/broken | FAIL/patch_did_not_apply | FAIL/broken |
| late_event_close | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |

## Cost, tokens, cache

Prefix cache can hit on k>1 even when k=1 unique pairs were meant to be uncached. A nonzero `cached_tokens` count is reported, not treated as contamination unless `comparable` is false.

| task | provider | trial | pass | quality | cost | prompt | completion | reason_tok | cached | latency_s |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| watermark_poison | novita | 1 | True | gold | 0.000170675 | 309 | 590 | 184 |  | 15.438 |
| watermark_poison | z-ai | 1 | True | gold | 0.000150565 | 309 | 571 | 166 | 256 | 13.264 |
| watermark_poison | deepinfra | 1 | True | gold | 0.000170925 | 309 | 591 | 215 |  | 12.577 |
| watermark_poison | gmicloud | 1 | True | equivalent | 0.000151175 | 309 | 512 | 101 |  | 16.438 |
| watermark_poison | novita | 2 | False |  |  |  |  |  |  |  |
| watermark_poison | z-ai | 2 | True | gold | 0.000159565 | 309 | 607 | 168 | 256 | 12.953 |
| watermark_poison | deepinfra | 2 | True | equivalent | 0.000184425 | 309 | 645 | 207 |  | 19.699 |
| watermark_poison | gmicloud | 2 | True | gold | 0.000154675 | 309 | 526 | 121 |  | 18.371 |
| watermark_poison | novita | 3 | True | gold | 0.000177925 | 309 | 619 | 202 |  | 17.787 |
| watermark_poison | z-ai | 3 | True | gold | 0.000159565 | 309 | 607 | 168 | 256 | 13.686 |
| watermark_poison | deepinfra | 3 | True | gold | 0.000159675 | 309 | 546 | 168 |  | 11.598 |
| watermark_poison | gmicloud | 3 | True | equivalent | 0.000173425 | 309 | 601 | 137 |  | 17.233 |
| entity_reload | novita | 1 | True | equivalent | 0.00023573 | 546 | 902 | 208 | 512 | 18.796 |
| entity_reload | z-ai | 1 | True | equivalent | 0.00021048 | 546 | 801 | 214 | 512 | 16.67 |
| entity_reload | deepinfra | 1 | True | equivalent | 0.0002372 | 546 | 785 | 172 |  | 24.571 |
| entity_reload | gmicloud | 1 | True | equivalent | 0.0002142 | 546 | 693 | 147 |  | 16.735 |
| entity_reload | novita | 2 | True | equivalent | 0.00018648 | 546 | 705 | 118 | 512 | 22.256 |
| entity_reload | z-ai | 2 | True | gold | 0.00021323 | 546 | 812 | 212 | 512 | 16.829 |
| entity_reload | deepinfra | 2 | True | gold | 0.00019895 | 546 | 632 | 106 |  | 27.623 |
| entity_reload | gmicloud | 2 | True | equivalent | 0.0002502 | 546 | 837 | 199 |  | 50.693 |
| entity_reload | novita | 3 | False |  |  |  |  |  |  |  |
| entity_reload | z-ai | 3 | True | gold | 0.00026798 | 546 | 1031 | 358 | 512 | 19.78 |
| entity_reload | deepinfra | 3 | True | gold | 0.0002447 | 546 | 815 | 197 |  | 17.202 |
| entity_reload | gmicloud | 3 | True | equivalent | 0.0002237 | 546 | 731 | 182 |  | 17.03 |
| frozen_basis | novita | 1 | False | broken | 0.000343225 | 383 | 1258 | 611 |  | 28.883 |
| frozen_basis | z-ai | 1 | False | broken | 0.000236275 | 383 | 907 | 260 | 320 | 17.299 |
| frozen_basis | deepinfra | 1 | False | broken | 0.000380475 | 383 | 1407 | 530 |  | 28.067 |
| frozen_basis | gmicloud | 1 | False | broken | 0.001349725 | 383 | 5284 | 4688 |  | 56.001 |
| frozen_basis | novita | 2 | False | broken | 0.000308475 | 383 | 1119 | 500 |  | 27.339 |
| frozen_basis | z-ai | 2 | False | broken | 0.000405525 | 383 | 1584 | 855 | 320 | 31.663 |
| frozen_basis | deepinfra | 2 | False | broken | 0.000381225 | 383 | 1410 | 660 |  | 28.801 |
| frozen_basis | gmicloud | 2 | False | broken | 0.001439725 | 383 | 5644 | 5081 |  | 176.949 |
| frozen_basis | novita | 3 | False | broken | 0.000230725 | 383 | 808 | 130 |  | 20.438 |
| frozen_basis | z-ai | 3 | False | broken | 0.000200275 | 383 | 763 | 152 | 320 | 17.383 |
| frozen_basis | deepinfra | 3 | False | broken | 0.000291975 | 383 | 1053 | 602 |  | 22.129 |
| frozen_basis | gmicloud | 3 | False | broken | 0.000374975 | 383 | 1385 | 715 |  | 42.822 |
| read_write_split | novita | 1 | True | gold | 0.00015995 | 406 | 518 | 83 |  | 11.381 |
| read_write_split | z-ai | 1 | True | gold | 0.00011841 | 406 | 444 | 65 | 384 | 10.562 |
| read_write_split | deepinfra | 1 | True | gold | 0.00014145 | 406 | 444 | 65 |  | 9.387 |
| read_write_split | gmicloud | 1 | True | gold | 0.00013745 | 406 | 428 | 49 |  | 11.149 |
| read_write_split | novita | 2 | True | gold | 0.0001622 | 406 | 527 | 59 |  | 11.759 |
| read_write_split | z-ai | 2 | True | gold | 0.00013841 | 406 | 524 | 85 | 384 | 10.586 |
| read_write_split | deepinfra | 2 | True | gold | 0.00016145 | 406 | 524 | 83 |  | 15.011 |
| read_write_split | gmicloud | 2 | True | gold | 0.00015445 | 406 | 496 | 68 |  | 38.041 |
| read_write_split | novita | 3 | True | gold | 0.0001512 | 406 | 483 | 50 |  | 12.333 |
| read_write_split | z-ai | 3 | True | gold | 0.00011341 | 406 | 424 | 49 | 384 | 9.705 |
| read_write_split | deepinfra | 3 | True | gold | 0.0001487 | 406 | 473 | 74 |  | 14.241 |
| read_write_split | gmicloud | 3 | True | equivalent | 0.00014645 | 406 | 464 | 48 |  | 15.503 |
| mtime_skip | novita | 1 | False | broken | 0.0002419 | 332 | 868 | 330 |  | 41.014 |
| mtime_skip | z-ai | 1 | True | equivalent | 0.0002057 | 332 | 800 | 239 | 320 | 19.608 |
| mtime_skip | deepinfra | 1 | True | equivalent | 0.00024765 | 332 | 891 | 447 |  | 22.877 |
| mtime_skip | gmicloud | 1 | True | equivalent | 0.00407265 | 332 | 16191 | 15691 |  | 397.215 |
| mtime_skip | novita | 2 | False | broken | 0.0001809 | 332 | 624 | 186 |  | 13.561 |
| mtime_skip | z-ai | 2 | True | equivalent | 0.00030945 | 332 | 1215 | 626 | 320 | 26.749 |
| mtime_skip | deepinfra | 2 | False | broken | 0.0001824 | 332 | 630 | 236 |  | 9.965 |
| mtime_skip | gmicloud | 2 | True | equivalent | 0.0001854 | 332 | 642 | 112 |  | 16.575 |
| mtime_skip | novita | 3 | True | equivalent | 0.00019915 | 332 | 697 | 235 |  | 15.499 |
| mtime_skip | z-ai | 3 | True | equivalent | 0.0002842 | 332 | 1114 | 422 | 320 | 23.426 |
| mtime_skip | deepinfra | 3 | True | equivalent | 0.00028415 | 332 | 1037 | 560 |  | 24.495 |
| mtime_skip | gmicloud | 3 | False | broken | 0.00019615 | 332 | 685 | 101 |  | 14.643 |
| rebuild_wipe | novita | 1 | False | broken | 0.0002351 | 288 | 854 | 303 |  | 30.869 |
| rebuild_wipe | z-ai | 1 | False | broken | 0.00081099 | 288 | 3219 | 2630 | 256 | 56.169 |
| rebuild_wipe | deepinfra | 1 | False | broken | 0.00025285 | 288 | 925 | 396 |  | 20.381 |
| rebuild_wipe | gmicloud | 1 | False | broken | 0.00019435 | 288 | 691 | 234 |  | 10.118 |
| rebuild_wipe | novita | 2 | True | equivalent | 0.0003281 | 288 | 1226 | 667 |  | 29.559 |
| rebuild_wipe | z-ai | 2 | False | broken | 0.00036924 | 288 | 1452 | 783 | 256 | 26.776 |
| rebuild_wipe | deepinfra | 2 | True | equivalent | 0.0003531 | 288 | 1326 | 811 |  | 27.787 |
| rebuild_wipe | gmicloud | 2 | True | equivalent | 0.00021185 | 288 | 761 | 298 |  | 17.127 |
| rebuild_wipe | novita | 3 | False | broken | 0.0001876 | 288 | 664 | 173 |  | 23.954 |
| rebuild_wipe | z-ai | 3 | False | broken | 0.00030574 | 288 | 1198 | 668 | 256 | 23.175 |
| rebuild_wipe | deepinfra | 3 | False | broken | 0.0004841 | 288 | 1850 | 1279 |  | 46.066 |
| rebuild_wipe | gmicloud | 3 | False | broken | 0.0002441 | 288 | 890 | 416 |  | 30.071 |
| drop_resurrect | novita | 1 | True | equivalent | 0.00018365 | 392 | 617 | 122 |  | 19.154 |
| drop_resurrect | z-ai | 1 | True | equivalent | 0.00012811 | 392 | 487 | 59 | 384 | 10.893 |
| drop_resurrect | deepinfra | 1 | True | equivalent | 0.00019115 | 392 | 647 | 110 |  | 14.661 |
| drop_resurrect | gmicloud | 1 | True | equivalent | 0.0001664 | 392 | 548 | 63 |  | 15.354 |
| drop_resurrect | novita | 2 | True | equivalent | 0.00020365 | 392 | 697 | 104 |  | 20.218 |
| drop_resurrect | z-ai | 2 | True | equivalent | 0.00014011 | 392 | 535 | 59 | 384 | 12.527 |
| drop_resurrect | deepinfra | 2 | True | equivalent | 0.0002039 | 392 | 698 | 154 |  | 18.885 |
| drop_resurrect | gmicloud | 2 | True | equivalent | 0.00022665 | 392 | 789 | 164 |  | 25.305 |
| drop_resurrect | novita | 3 | True | equivalent | 0.0002214 | 392 | 768 | 182 |  | 16.675 |
| drop_resurrect | z-ai | 3 | True | equivalent | 0.00016711 | 392 | 643 | 146 | 384 | 13.765 |
| drop_resurrect | deepinfra | 3 | True | equivalent | 0.00019365 | 392 | 657 | 155 |  | 15.767 |
| drop_resurrect | gmicloud | 3 | True | equivalent | 0.0002044 | 392 | 700 | 114 |  | 15.426 |
| field_readd | novita | 1 | False | patch_did_not_apply | 0.000163155 | 555 | 609 | 143 | 512 | 19.59 |
| field_readd | z-ai | 1 | False | patch_did_not_apply | 0.000204405 | 555 | 774 | 360 | 512 | 15.444 |
| field_readd | deepinfra | 1 | True | equivalent | 0.000218875 | 555 | 709 | 152 |  | 18.794 |
| field_readd | gmicloud | 1 | False | patch_did_not_apply | 0.000182625 | 555 | 564 | 132 |  | 14.274 |
| field_readd | novita | 2 | False | patch_did_not_apply | 0.000189655 | 555 | 715 | 212 | 512 | 14.868 |
| field_readd | z-ai | 2 | True | equivalent | 0.000190655 | 555 | 719 | 167 | 512 | 15.74 |
| field_readd | deepinfra | 2 | False | patch_did_not_apply | 0.000208875 | 555 | 669 | 149 |  | 12.586 |
| field_readd | gmicloud | 2 | False | patch_did_not_apply | 0.000172405 | 555 | 646 | 220 | 512 | 15.454 |
| field_readd | novita | 3 | True | equivalent | 0.000205905 | 555 | 780 | 360 | 512 | 16.729 |
| field_readd | z-ai | 3 | True | equivalent | 0.000252655 | 555 | 967 | 367 | 512 | 19.207 |
| field_readd | deepinfra | 3 | True | equivalent | 0.000208625 | 555 | 668 | 183 |  | 16.533 |
| field_readd | gmicloud | 3 | True | equivalent | 0.002780625 | 555 | 10956 | 10365 |  | 220.038 |
| late_event_close | novita | 1 | False | broken | 0.0003699 | 542 | 1317 | 672 |  | 27.441 |
| late_event_close | z-ai | 1 | False | broken | 0.00023418 | 542 | 897 | 357 | 512 | 19.693 |
| late_event_close | deepinfra | 1 | False | broken | 0.00103115 | 542 | 3962 | 3604 |  | 114.016 |
| late_event_close | gmicloud | 1 | False | patch_did_not_apply | 0.00365715 | 542 | 14466 | 12635 |  | 219.675 |
| late_event_close | novita | 2 | False | broken | 0.00023418 | 542 | 897 | 357 | 512 | 18.966 |
| late_event_close | z-ai | 2 | False | broken | 0.00233368 | 542 | 9295 | 8374 | 512 | 178.82 |
| late_event_close | deepinfra | 2 | False | patch_did_not_apply | 0.00047165 | 542 | 1724 | 1171 |  | 34.288 |
| late_event_close | gmicloud | 2 | False | broken | 0.00063215 | 542 | 2366 | 1663 |  | 53.224 |
| late_event_close | novita | 3 | False | broken | 0.00023493 | 542 | 900 | 357 | 512 | 35.093 |
| late_event_close | z-ai | 3 | False | broken | 0.00056118 | 542 | 2205 | 1462 | 512 | 42.208 |
| late_event_close | deepinfra | 3 | False | broken | 0.0004804 | 542 | 1759 | 976 |  | 28.724 |
| late_event_close | gmicloud | 3 | False | broken | 0.00047118 | 542 | 1845 | 1152 | 512 | 43.063 |

## What this can and cannot say

Same applied sha across hosts on a PASS means they emitted the same repair, not that they thought the same. CoT is one concatenated stream on disk (`logs/raw-*.json`). Format-fail is a host outcome when the candidate had no usable hunk after unwrap.

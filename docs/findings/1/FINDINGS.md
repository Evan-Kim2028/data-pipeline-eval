# Findings 1

Run `20260829T224943Z + 20260829T230214Z`  model `z-ai/glm-5.3-flash`  k=`3`  comparable=`True`  sha `ee28e391fdfc2194627367be89fd11a355c3fa48 0f1aa9d5ad2cbd7e92cf011669dca2a864f84907`  n=`108`  spend~$0.0405.

This eval is one-shot. The model returns one unified diff. There are no tool calls and no agent-loop hop spans. Logic hops below are paragraph/claim cuts of the CoT blob. TPS is tokens per wall-clock second of the HTTP stream (`completion_tokens / latency_s`, `reasoning_tokens / latency_s`).

Do not read a winner rank out of these rates. k is small. Several tasks stay red on both hosts.

## Pass and quality

| provider | pass | rate | gold | equivalent | broken | format | infra |
|---|---:|---:|---:|---:|---:|---:|---:|
| novita | 13/27 | 0.481 | 5 | 8 | 10 | 0 | 2 |
| z-ai | 17/27 | 0.630 | 8 | 9 | 9 | 0 | 0 |
| deepinfra | 17/27 | 0.630 | 7 | 10 | 8 | 0 | 0 |
| gmicloud | 16/27 | 0.593 | 3 | 13 | 8 | 0 | 0 |

## Cost, tokens, TPS

| provider | cost sum | prompt tok | completion tok | reason tok | total tok | mean cached | cached>0 | mean latency_s | mean tps_out | mean tps_reason | mean hops |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| novita | 0.0055 | 10404 | 19762 | 6548 | 30166 | 143.4 | 7 | 21.2 | 39.0 | 11.9 | 4.8 |
| z-ai | 0.0089 | 11259 | 34595 | 19471 | 45854 | 384.0 | 27 | 25.7 | 47.8 | 17.9 | 13.0 |
| deepinfra | 0.0077 | 11259 | 27477 | 13462 | 38736 | 0.0 | 0 | 24.3 | 43.3 | 16.7 | 8.3 |
| gmicloud | 0.0184 | 11259 | 70341 | 54896 | 81600 | 37.9 | 2 | 58.7 | 40.8 | 18.3 | 39.5 |

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

## Per trial tokens

Prefix cache can hit on k>1. Nonzero `cached_tokens` is reported, not contamination unless `comparable` is false. `tps_out` is completion tokens per second. `hops` are CoT claim/paragraph cuts.

| task | provider | trial | pass | quality | cost | prompt | completion | reason_tok | hops | tps_out | cached | latency_s |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| watermark_poison | novita | 1 | True | gold | 0.000170675 | 309 | 590 | 184 | 5 | 38.217 |  | 15.438 |
| watermark_poison | z-ai | 1 | True | gold | 0.000150565 | 309 | 571 | 166 | 4 | 43.049 | 256 | 13.264 |
| watermark_poison | deepinfra | 1 | True | gold | 0.000170925 | 309 | 591 | 215 | 5 | 46.991 |  | 12.577 |
| watermark_poison | gmicloud | 1 | True | equivalent | 0.000151175 | 309 | 512 | 101 | 3 | 31.147 |  | 16.438 |
| watermark_poison | novita | 2 | False |  |  |  |  |  |  |  |  |  |
| watermark_poison | z-ai | 2 | True | gold | 0.000159565 | 309 | 607 | 168 | 4 | 46.862 | 256 | 12.953 |
| watermark_poison | deepinfra | 2 | True | equivalent | 0.000184425 | 309 | 645 | 207 | 4 | 32.743 |  | 19.699 |
| watermark_poison | gmicloud | 2 | True | gold | 0.000154675 | 309 | 526 | 121 | 3 | 28.632 |  | 18.371 |
| watermark_poison | novita | 3 | True | gold | 0.000177925 | 309 | 619 | 202 | 4 | 34.801 |  | 17.787 |
| watermark_poison | z-ai | 3 | True | gold | 0.000159565 | 309 | 607 | 168 | 4 | 44.352 | 256 | 13.686 |
| watermark_poison | deepinfra | 3 | True | gold | 0.000159675 | 309 | 546 | 168 | 4 | 47.077 |  | 11.598 |
| watermark_poison | gmicloud | 3 | True | equivalent | 0.000173425 | 309 | 601 | 137 | 3 | 34.875 |  | 17.233 |
| entity_reload | novita | 1 | True | equivalent | 0.00023573 | 546 | 902 | 208 | 5 | 47.989 | 512 | 18.796 |
| entity_reload | z-ai | 1 | True | equivalent | 0.00021048 | 546 | 801 | 214 | 5 | 48.05 | 512 | 16.67 |
| entity_reload | deepinfra | 1 | True | equivalent | 0.0002372 | 546 | 785 | 172 | 5 | 31.948 |  | 24.571 |
| entity_reload | gmicloud | 1 | True | equivalent | 0.0002142 | 546 | 693 | 147 | 4 | 41.41 |  | 16.735 |
| entity_reload | novita | 2 | True | equivalent | 0.00018648 | 546 | 705 | 118 | 3 | 31.677 | 512 | 22.256 |
| entity_reload | z-ai | 2 | True | gold | 0.00021323 | 546 | 812 | 212 | 5 | 48.25 | 512 | 16.829 |
| entity_reload | deepinfra | 2 | True | gold | 0.00019895 | 546 | 632 | 106 | 3 | 22.879 |  | 27.623 |
| entity_reload | gmicloud | 2 | True | equivalent | 0.0002502 | 546 | 837 | 199 | 5 | 16.511 |  | 50.693 |
| entity_reload | novita | 3 | False |  |  |  |  |  |  |  |  |  |
| entity_reload | z-ai | 3 | True | gold | 0.00026798 | 546 | 1031 | 358 | 10 | 52.123 | 512 | 19.78 |
| entity_reload | deepinfra | 3 | True | gold | 0.0002447 | 546 | 815 | 197 | 4 | 47.378 |  | 17.202 |
| entity_reload | gmicloud | 3 | True | equivalent | 0.0002237 | 546 | 731 | 182 | 4 | 42.924 |  | 17.03 |
| frozen_basis | novita | 1 | False | broken | 0.000343225 | 383 | 1258 | 611 | 10 | 43.555 |  | 28.883 |
| frozen_basis | z-ai | 1 | False | broken | 0.000236275 | 383 | 907 | 260 | 5 | 52.431 | 320 | 17.299 |
| frozen_basis | deepinfra | 1 | False | broken | 0.000380475 | 383 | 1407 | 530 | 11 | 50.13 |  | 28.067 |
| frozen_basis | gmicloud | 1 | False | broken | 0.001349725 | 383 | 5284 | 4688 | 86 | 94.355 |  | 56.001 |
| frozen_basis | novita | 2 | False | broken | 0.000308475 | 383 | 1119 | 500 | 7 | 40.931 |  | 27.339 |
| frozen_basis | z-ai | 2 | False | broken | 0.000405525 | 383 | 1584 | 855 | 17 | 50.027 | 320 | 31.663 |
| frozen_basis | deepinfra | 2 | False | broken | 0.000381225 | 383 | 1410 | 660 | 14 | 48.957 |  | 28.801 |
| frozen_basis | gmicloud | 2 | False | broken | 0.001439725 | 383 | 5644 | 5081 | 79 | 31.896 |  | 176.949 |
| frozen_basis | novita | 3 | False | broken | 0.000230725 | 383 | 808 | 130 | 3 | 39.534 |  | 20.438 |
| frozen_basis | z-ai | 3 | False | broken | 0.000200275 | 383 | 763 | 152 | 3 | 43.893 | 320 | 17.383 |
| frozen_basis | deepinfra | 3 | False | broken | 0.000291975 | 383 | 1053 | 602 | 8 | 47.585 |  | 22.129 |
| frozen_basis | gmicloud | 3 | False | broken | 0.000374975 | 383 | 1385 | 715 | 12 | 32.343 |  | 42.822 |
| read_write_split | novita | 1 | True | gold | 0.00015995 | 406 | 518 | 83 | 2 | 45.514 |  | 11.381 |
| read_write_split | z-ai | 1 | True | gold | 0.00011841 | 406 | 444 | 65 | 2 | 42.037 | 384 | 10.562 |
| read_write_split | deepinfra | 1 | True | gold | 0.00014145 | 406 | 444 | 65 | 2 | 47.299 |  | 9.387 |
| read_write_split | gmicloud | 1 | True | gold | 0.00013745 | 406 | 428 | 49 | 2 | 38.389 |  | 11.149 |
| read_write_split | novita | 2 | True | gold | 0.0001622 | 406 | 527 | 59 | 2 | 44.817 |  | 11.759 |
| read_write_split | z-ai | 2 | True | gold | 0.00013841 | 406 | 524 | 85 | 2 | 49.499 | 384 | 10.586 |
| read_write_split | deepinfra | 2 | True | gold | 0.00016145 | 406 | 524 | 83 | 2 | 34.908 |  | 15.011 |
| read_write_split | gmicloud | 2 | True | gold | 0.00015445 | 406 | 496 | 68 | 2 | 13.039 |  | 38.041 |
| read_write_split | novita | 3 | True | gold | 0.0001512 | 406 | 483 | 50 | 1 | 39.163 |  | 12.333 |
| read_write_split | z-ai | 3 | True | gold | 0.00011341 | 406 | 424 | 49 | 2 | 43.689 | 384 | 9.705 |
| read_write_split | deepinfra | 3 | True | gold | 0.0001487 | 406 | 473 | 74 | 2 | 33.214 |  | 14.241 |
| read_write_split | gmicloud | 3 | True | equivalent | 0.00014645 | 406 | 464 | 48 | 2 | 29.93 |  | 15.503 |
| mtime_skip | novita | 1 | False | broken | 0.0002419 | 332 | 868 | 330 | 5 | 21.164 |  | 41.014 |
| mtime_skip | z-ai | 1 | True | equivalent | 0.0002057 | 332 | 800 | 239 | 4 | 40.8 | 320 | 19.608 |
| mtime_skip | deepinfra | 1 | True | equivalent | 0.00024765 | 332 | 891 | 447 | 6 | 38.947 |  | 22.877 |
| mtime_skip | gmicloud | 1 | True | equivalent | 0.00407265 | 332 | 16191 | 15691 | 338 | 40.761 |  | 397.215 |
| mtime_skip | novita | 2 | False | broken | 0.0001809 | 332 | 624 | 186 | 3 | 46.014 |  | 13.561 |
| mtime_skip | z-ai | 2 | True | equivalent | 0.00030945 | 332 | 1215 | 626 | 11 | 45.422 | 320 | 26.749 |
| mtime_skip | deepinfra | 2 | False | broken | 0.0001824 | 332 | 630 | 236 | 5 | 63.221 |  | 9.965 |
| mtime_skip | gmicloud | 2 | True | equivalent | 0.0001854 | 332 | 642 | 112 | 2 | 38.733 |  | 16.575 |
| mtime_skip | novita | 3 | True | equivalent | 0.00019915 | 332 | 697 | 235 | 3 | 44.971 |  | 15.499 |
| mtime_skip | z-ai | 3 | True | equivalent | 0.0002842 | 332 | 1114 | 422 | 5 | 47.554 | 320 | 23.426 |
| mtime_skip | deepinfra | 3 | True | equivalent | 0.00028415 | 332 | 1037 | 560 | 8 | 42.335 |  | 24.495 |
| mtime_skip | gmicloud | 3 | False | broken | 0.00019615 | 332 | 685 | 101 | 2 | 46.78 |  | 14.643 |
| rebuild_wipe | novita | 1 | False | broken | 0.0002351 | 288 | 854 | 303 | 4 | 27.665 |  | 30.869 |
| rebuild_wipe | z-ai | 1 | False | broken | 0.00081099 | 288 | 3219 | 2630 | 54 | 57.309 | 256 | 56.169 |
| rebuild_wipe | deepinfra | 1 | False | broken | 0.00025285 | 288 | 925 | 396 | 12 | 45.385 |  | 20.381 |
| rebuild_wipe | gmicloud | 1 | False | broken | 0.00019435 | 288 | 691 | 234 | 7 | 68.294 |  | 10.118 |
| rebuild_wipe | novita | 2 | True | equivalent | 0.0003281 | 288 | 1226 | 667 | 9 | 41.476 |  | 29.559 |
| rebuild_wipe | z-ai | 2 | False | broken | 0.00036924 | 288 | 1452 | 783 | 13 | 54.228 | 256 | 26.776 |
| rebuild_wipe | deepinfra | 2 | True | equivalent | 0.0003531 | 288 | 1326 | 811 | 15 | 47.72 |  | 27.787 |
| rebuild_wipe | gmicloud | 2 | True | equivalent | 0.00021185 | 288 | 761 | 298 | 7 | 44.433 |  | 17.127 |
| rebuild_wipe | novita | 3 | False | broken | 0.0001876 | 288 | 664 | 173 | 3 | 27.72 |  | 23.954 |
| rebuild_wipe | z-ai | 3 | False | broken | 0.00030574 | 288 | 1198 | 668 | 12 | 51.694 | 256 | 23.175 |
| rebuild_wipe | deepinfra | 3 | False | broken | 0.0004841 | 288 | 1850 | 1279 | 20 | 40.16 |  | 46.066 |
| rebuild_wipe | gmicloud | 3 | False | broken | 0.0002441 | 288 | 890 | 416 | 6 | 29.597 |  | 30.071 |
| drop_resurrect | novita | 1 | True | equivalent | 0.00018365 | 392 | 617 | 122 | 3 | 32.213 |  | 19.154 |
| drop_resurrect | z-ai | 1 | True | equivalent | 0.00012811 | 392 | 487 | 59 | 2 | 44.708 | 384 | 10.893 |
| drop_resurrect | deepinfra | 1 | True | equivalent | 0.00019115 | 392 | 647 | 110 | 3 | 44.131 |  | 14.661 |
| drop_resurrect | gmicloud | 1 | True | equivalent | 0.0001664 | 392 | 548 | 63 | 2 | 35.691 |  | 15.354 |
| drop_resurrect | novita | 2 | True | equivalent | 0.00020365 | 392 | 697 | 104 | 3 | 34.474 |  | 20.218 |
| drop_resurrect | z-ai | 2 | True | equivalent | 0.00014011 | 392 | 535 | 59 | 2 | 42.708 | 384 | 12.527 |
| drop_resurrect | deepinfra | 2 | True | equivalent | 0.0002039 | 392 | 698 | 154 | 4 | 36.961 |  | 18.885 |
| drop_resurrect | gmicloud | 2 | True | equivalent | 0.00022665 | 392 | 789 | 164 | 3 | 31.18 |  | 25.305 |
| drop_resurrect | novita | 3 | True | equivalent | 0.0002214 | 392 | 768 | 182 | 4 | 46.057 |  | 16.675 |
| drop_resurrect | z-ai | 3 | True | equivalent | 0.00016711 | 392 | 643 | 146 | 3 | 46.713 | 384 | 13.765 |
| drop_resurrect | deepinfra | 3 | True | equivalent | 0.00019365 | 392 | 657 | 155 | 3 | 41.669 |  | 15.767 |
| drop_resurrect | gmicloud | 3 | True | equivalent | 0.0002044 | 392 | 700 | 114 | 3 | 45.378 |  | 15.426 |
| field_readd | novita | 1 | False | patch_did_not_apply | 0.000163155 | 555 | 609 | 143 | 4 | 31.087 | 512 | 19.59 |
| field_readd | z-ai | 1 | False | patch_did_not_apply | 0.000204405 | 555 | 774 | 360 | 7 | 50.117 | 512 | 15.444 |
| field_readd | deepinfra | 1 | True | equivalent | 0.000218875 | 555 | 709 | 152 | 5 | 37.725 |  | 18.794 |
| field_readd | gmicloud | 1 | False | patch_did_not_apply | 0.000182625 | 555 | 564 | 132 | 3 | 39.512 |  | 14.274 |
| field_readd | novita | 2 | False | patch_did_not_apply | 0.000189655 | 555 | 715 | 212 | 5 | 48.09 | 512 | 14.868 |
| field_readd | z-ai | 2 | True | equivalent | 0.000190655 | 555 | 719 | 167 | 5 | 45.68 | 512 | 15.74 |
| field_readd | deepinfra | 2 | False | patch_did_not_apply | 0.000208875 | 555 | 669 | 149 | 4 | 53.154 |  | 12.586 |
| field_readd | gmicloud | 2 | False | patch_did_not_apply | 0.000172405 | 555 | 646 | 220 | 5 | 41.801 | 512 | 15.454 |
| field_readd | novita | 3 | True | equivalent | 0.000205905 | 555 | 780 | 360 | 7 | 46.626 | 512 | 16.729 |
| field_readd | z-ai | 3 | True | equivalent | 0.000252655 | 555 | 967 | 367 | 5 | 50.346 | 512 | 19.207 |
| field_readd | deepinfra | 3 | True | equivalent | 0.000208625 | 555 | 668 | 183 | 5 | 40.404 |  | 16.533 |
| field_readd | gmicloud | 3 | True | equivalent | 0.002780625 | 555 | 10956 | 10365 | 240 | 49.791 |  | 220.038 |
| late_event_close | novita | 1 | False | broken | 0.0003699 | 542 | 1317 | 672 | 12 | 47.994 |  | 27.441 |
| late_event_close | z-ai | 1 | False | broken | 0.00023418 | 542 | 897 | 357 | 7 | 45.549 | 512 | 19.693 |
| late_event_close | deepinfra | 1 | False | broken | 0.00103115 | 542 | 3962 | 3604 | 44 | 34.75 |  | 114.016 |
| late_event_close | gmicloud | 1 | False | patch_did_not_apply | 0.00365715 | 542 | 14466 | 12635 | 194 | 65.852 |  | 219.675 |
| late_event_close | novita | 2 | False | broken | 0.00023418 | 542 | 897 | 357 | 7 | 47.295 | 512 | 18.966 |
| late_event_close | z-ai | 2 | False | broken | 0.00233368 | 542 | 9295 | 8374 | 137 | 51.98 | 512 | 178.82 |
| late_event_close | deepinfra | 2 | False | patch_did_not_apply | 0.00047165 | 542 | 1724 | 1171 | 15 | 50.28 |  | 34.288 |
| late_event_close | gmicloud | 2 | False | broken | 0.00063215 | 542 | 2366 | 1663 | 30 | 44.454 |  | 53.224 |
| late_event_close | novita | 3 | False | broken | 0.00023493 | 542 | 900 | 357 | 7 | 25.646 | 512 | 35.093 |
| late_event_close | z-ai | 3 | False | broken | 0.00056118 | 542 | 2205 | 1462 | 22 | 52.241 | 512 | 42.208 |
| late_event_close | deepinfra | 3 | False | broken | 0.0004804 | 542 | 1759 | 976 | 12 | 61.238 |  | 28.724 |
| late_event_close | gmicloud | 3 | False | broken | 0.00047118 | 542 | 1845 | 1152 | 19 | 42.844 | 512 | 43.063 |

## What this can and cannot say

Same applied sha across hosts on a PASS means they emitted the same repair, not that they thought the same. CoT is one concatenated stream on disk (`logs/raw-*.json`). Format-fail is a host outcome when the candidate had no usable hunk after unwrap.

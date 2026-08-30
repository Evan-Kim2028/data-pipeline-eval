# Findings 2

Run `20260830T000722Z`  model `z-ai/glm-5.3-flash`  k=`3`  comparable=`True`  sha `68930c72cc7ac6036fa5365af3c0af2d2aace242`  n=`108`  spend~$0.0345.

This eval is one-shot. The model returns one unified diff. There are no tool calls and no agent-loop hop spans. Logic hops below are paragraph/claim cuts of the CoT blob. TPS is tokens per wall-clock second of the HTTP stream (`completion_tokens / latency_s`, `reasoning_tokens / latency_s`).

Do not read a winner rank out of these rates. k is small. Several tasks stay red on both hosts.

## Pass and quality

| provider | pass | rate | gold | equivalent | broken | format | infra |
|---|---:|---:|---:|---:|---:|---:|---:|
| deepinfra | 14/27 | 0.519 | 9 | 5 | 10 | 0 | 0 |
| gmicloud | 15/27 | 0.556 | 7 | 8 | 10 | 0 | 0 |
| novita | 13/27 | 0.481 | 3 | 10 | 9 | 0 | 2 |
| z-ai | 15/27 | 0.556 | 6 | 9 | 10 | 0 | 0 |

## Cost, tokens, TPS

| provider | cost sum | prompt tok | completion tok | reason tok | total tok | mean cached | cached>0 | mean latency_s | mean tps_out | mean tps_reason | mean hops |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepinfra | 0.0099 | 11259 | 36237 | 24232 | 47496 | 0.0 | 0 | 30.9 | 45.0 | 18.7 | 14.1 |
| gmicloud | 0.0088 | 11259 | 32868 | 18739 | 44127 | 132.7 | 7 | 32.7 | 39.3 | 14.5 | 12.0 |
| novita | 0.0071 | 10544 | 26232 | 12505 | 36776 | 163.8 | 8 | 30.5 | 37.1 | 13.7 | 8.2 |
| z-ai | 0.0086 | 11259 | 32712 | 17722 | 43971 | 256.0 | 18 | 28.4 | 42.1 | 15.1 | 11.6 |

## Per task / trial

| task | trial | deepinfra | gmicloud | novita | z-ai |
|---|---|---|---|---|---|
| watermark_poison | 1 | PASS/equivalent | PASS/equivalent | FAIL/ | PASS/gold |
| watermark_poison | 2 | PASS/gold | PASS/equivalent | PASS/gold | PASS/gold |
| watermark_poison | 3 | PASS/gold | PASS/gold | PASS/equivalent | PASS/equivalent |
| entity_reload | 1 | PASS/gold | PASS/gold | PASS/equivalent | PASS/gold |
| entity_reload | 2 | PASS/gold | PASS/gold | PASS/equivalent | PASS/equivalent |
| entity_reload | 3 | PASS/gold | PASS/gold | PASS/equivalent | PASS/gold |
| frozen_basis | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| frozen_basis | 2 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| frozen_basis | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| read_write_split | 1 | PASS/gold | PASS/gold | PASS/gold | PASS/gold |
| read_write_split | 2 | PASS/gold | PASS/gold | PASS/gold | PASS/equivalent |
| read_write_split | 3 | PASS/gold | PASS/gold | FAIL/ | PASS/gold |
| mtime_skip | 1 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| mtime_skip | 2 | FAIL/broken | FAIL/broken | PASS/equivalent | PASS/equivalent |
| mtime_skip | 3 | PASS/gold | PASS/equivalent | PASS/equivalent | FAIL/broken |
| rebuild_wipe | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| rebuild_wipe | 2 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| rebuild_wipe | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| drop_resurrect | 1 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| drop_resurrect | 2 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| drop_resurrect | 3 | PASS/equivalent | PASS/equivalent | PASS/equivalent | PASS/equivalent |
| field_readd | 1 | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply |
| field_readd | 2 | FAIL/patch_did_not_apply | PASS/equivalent | FAIL/patch_did_not_apply | PASS/equivalent |
| field_readd | 3 | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply | FAIL/patch_did_not_apply |
| late_event_close | 1 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| late_event_close | 2 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |
| late_event_close | 3 | FAIL/broken | FAIL/broken | FAIL/broken | FAIL/broken |

## Per trial tokens

Prefix cache can hit on k>1. Nonzero `cached_tokens` is reported, not contamination unless `comparable` is false. `tps_out` is completion tokens per second. `hops` are CoT claim/paragraph cuts.

| task | provider | trial | pass | quality | cost | prompt | completion | reason_tok | hops | tps_out | cached | latency_s |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| watermark_poison | deepinfra | 1 | True | equivalent | 0.000174175 | 309 | 604 | 181 | 4 | 58.692 |  | 10.291 |
| watermark_poison | gmicloud | 1 | True | equivalent | 0.000171925 | 309 | 595 | 127 | 3 | 24.404 |  | 24.381 |
| watermark_poison | novita | 1 | False |  |  |  |  |  |  |  |  |  |
| watermark_poison | z-ai | 1 | True | gold | 0.000137315 | 309 | 518 | 127 | 4 | 34.239 | 256 | 15.129 |
| watermark_poison | deepinfra | 2 | True | gold | 0.000154175 | 309 | 524 | 156 | 4 | 36.875 |  | 14.21 |
| watermark_poison | gmicloud | 2 | True | equivalent | 0.000172675 | 309 | 598 | 186 | 6 | 24.779 |  | 24.133 |
| watermark_poison | novita | 2 | True | gold | 0.000179175 | 309 | 624 | 188 | 4 | 41.018 |  | 15.213 |
| watermark_poison | z-ai | 2 | True | gold | 0.000156065 | 309 | 593 | 159 | 4 | 43.285 | 256 | 13.7 |
| watermark_poison | deepinfra | 3 | True | gold | 0.000188925 | 309 | 663 | 255 | 6 | 54.586 |  | 12.146 |
| watermark_poison | gmicloud | 3 | True | gold | 0.000139675 | 309 | 466 | 74 | 2 | 34.137 |  | 13.651 |
| watermark_poison | novita | 3 | True | equivalent | 0.000200175 | 309 | 708 | 230 | 7 | 32.307 |  | 21.915 |
| watermark_poison | z-ai | 3 | True | equivalent | 0.000160425 | 309 | 549 | 172 | 5 | 42.296 |  | 12.98 |
| entity_reload | deepinfra | 1 | True | gold | 0.0002072 | 546 | 665 | 150 | 4 | 38.921 |  | 17.086 |
| entity_reload | gmicloud | 1 | True | gold | 0.00019998 | 546 | 759 | 191 | 3 | 30.446 | 512 | 24.929 |
| entity_reload | novita | 1 | True | equivalent | 0.00021798 | 546 | 831 | 164 | 3 | 46.783 | 512 | 17.763 |
| entity_reload | z-ai | 1 | True | gold | 0.0002502 | 546 | 837 | 203 | 5 | 45.951 |  | 18.215 |
| entity_reload | deepinfra | 2 | True | gold | 0.00023595 | 546 | 780 | 171 | 3 | 48.498 |  | 16.083 |
| entity_reload | gmicloud | 2 | True | gold | 0.0002277 | 546 | 747 | 181 | 4 | 75.333 |  | 9.916 |
| entity_reload | novita | 2 | True | equivalent | 0.00018373 | 546 | 694 | 176 | 4 | 44.382 | 512 | 15.637 |
| entity_reload | z-ai | 2 | True | equivalent | 0.00020998 | 546 | 799 | 209 | 5 | 46.268 | 512 | 17.269 |
| entity_reload | deepinfra | 3 | True | gold | 0.00022395 | 546 | 732 | 164 | 4 | 67.261 |  | 10.883 |
| entity_reload | gmicloud | 3 | True | gold | 0.00018473 | 546 | 698 | 172 | 4 | 41.373 | 512 | 16.871 |
| entity_reload | novita | 3 | True | equivalent | 0.00024198 | 546 | 927 | 318 | 8 | 37.45 | 512 | 24.753 |
| entity_reload | z-ai | 3 | True | gold | 0.00023248 | 546 | 889 | 241 | 4 | 47.532 | 512 | 18.703 |
| frozen_basis | deepinfra | 1 | False | broken | 0.000642975 | 383 | 2457 | 1918 | 34 | 44.88 |  | 54.746 |
| frozen_basis | gmicloud | 1 | False | broken | 0.000410475 | 383 | 1527 | 845 | 14 | 32.021 |  | 47.688 |
| frozen_basis | novita | 1 | False | broken | 0.000384475 | 383 | 1423 | 794 | 15 | 54.402 |  | 26.157 |
| frozen_basis | z-ai | 1 | False | broken | 0.000381725 | 383 | 1412 | 773 | 13 | 23.631 |  | 59.752 |
| frozen_basis | deepinfra | 2 | False | broken | 0.000754725 | 383 | 2904 | 2473 | 40 | 41.907 |  | 69.296 |
| frozen_basis | gmicloud | 2 | False | broken | 0.000406475 | 383 | 1511 | 1020 | 13 | 46.081 |  | 32.79 |
| frozen_basis | novita | 2 | False | broken | 0.000396225 | 383 | 1470 | 652 | 14 | 51.045 |  | 28.798 |
| frozen_basis | z-ai | 2 | False | broken | 0.000648775 | 383 | 2557 | 1767 | 30 | 49.302 | 320 | 51.864 |
| frozen_basis | deepinfra | 3 | False | broken | 0.000591725 | 383 | 2252 | 1765 | 28 | 52.581 |  | 42.829 |
| frozen_basis | gmicloud | 3 | False | broken | 0.000613975 | 383 | 2341 | 1428 | 24 | 84.446 |  | 27.722 |
| frozen_basis | novita | 3 | False | broken | 0.000759475 | 383 | 2923 | 2284 | 27 | 41.027 |  | 71.246 |
| frozen_basis | z-ai | 3 | False | broken | 0.000627275 | 383 | 2471 | 1614 | 28 | 44.802 | 320 | 55.154 |
| read_write_split | deepinfra | 1 | True | gold | 0.00015095 | 406 | 482 | 73 | 2 | 34.971 |  | 13.783 |
| read_write_split | gmicloud | 1 | True | gold | 0.0001407 | 406 | 441 | 48 | 2 | 33.029 |  | 13.352 |
| read_write_split | novita | 1 | True | gold | 0.0001442 | 406 | 455 | 61 | 1 | 34.512 |  | 13.184 |
| read_write_split | z-ai | 1 | True | gold | 0.00012545 | 406 | 380 | 44 | 1 | 41.13 |  | 9.239 |
| read_write_split | deepinfra | 2 | True | gold | 0.0001592 | 406 | 515 | 62 | 1 | 49.519 |  | 10.4 |
| read_write_split | gmicloud | 2 | True | gold | 0.0001312 | 406 | 403 | 56 | 1 | 38.458 |  | 10.479 |
| read_write_split | novita | 2 | True | gold | 0.0001492 | 406 | 475 | 71 | 1 | 40.45 |  | 11.743 |
| read_write_split | z-ai | 2 | True | equivalent | 0.00014366 | 406 | 545 | 63 | 2 | 38.133 | 384 | 14.292 |
| read_write_split | deepinfra | 3 | True | gold | 0.00013845 | 406 | 432 | 62 | 1 | 50.961 |  | 8.477 |
| read_write_split | gmicloud | 3 | True | gold | 0.00015845 | 406 | 512 | 134 | 3 | 46.579 |  | 10.992 |
| read_write_split | novita | 3 | False |  |  |  |  |  |  |  |  |  |
| read_write_split | z-ai | 3 | True | gold | 0.00014316 | 406 | 543 | 63 | 2 | 37.703 | 384 | 14.402 |
| mtime_skip | deepinfra | 1 | True | equivalent | 0.00023015 | 332 | 821 | 361 | 4 | 18.524 |  | 44.32 |
| mtime_skip | gmicloud | 1 | True | equivalent | 0.0002704 | 332 | 982 | 477 | 5 | 31.052 |  | 31.624 |
| mtime_skip | novita | 1 | True | equivalent | 0.00019365 | 332 | 675 | 211 | 2 | 35.335 |  | 19.103 |
| mtime_skip | z-ai | 1 | True | equivalent | 0.00055915 | 332 | 2137 | 1532 | 16 | 39.45 |  | 54.17 |
| mtime_skip | deepinfra | 2 | False | broken | 0.00028065 | 332 | 1023 | 535 | 4 | 45.227 |  | 22.619 |
| mtime_skip | gmicloud | 2 | False | broken | 0.00024815 | 332 | 893 | 469 | 8 | 18.434 |  | 48.443 |
| mtime_skip | novita | 2 | True | equivalent | 0.00054515 | 332 | 2081 | 1419 | 19 | 49.178 |  | 42.316 |
| mtime_skip | z-ai | 2 | True | equivalent | 0.0002092 | 332 | 814 | 319 | 7 | 46.782 | 320 | 17.4 |
| mtime_skip | deepinfra | 3 | True | gold | 0.0002004 | 332 | 702 | 331 | 5 | 51.174 |  | 13.718 |
| mtime_skip | gmicloud | 3 | True | equivalent | 0.0002119 | 332 | 748 | 245 | 3 | 42.738 |  | 17.502 |
| mtime_skip | novita | 3 | True | equivalent | 0.0001844 | 332 | 638 | 208 | 5 | 43.612 |  | 14.629 |
| mtime_skip | z-ai | 3 | False | broken | 0.00022995 | 332 | 897 | 327 | 6 | 43.386 | 320 | 20.675 |
| rebuild_wipe | deepinfra | 1 | False | broken | 0.0002446 | 288 | 892 | 418 | 11 | 30.226 |  | 29.511 |
| rebuild_wipe | gmicloud | 1 | False | broken | 0.0003286 | 288 | 1228 | 555 | 11 | 46.475 |  | 26.423 |
| rebuild_wipe | novita | 1 | False | broken | 0.0002021 | 288 | 722 | 221 | 5 | 19.582 |  | 36.871 |
| rebuild_wipe | z-ai | 1 | False | broken | 0.00017735 | 288 | 623 | 183 | 5 | 39.933 |  | 15.601 |
| rebuild_wipe | deepinfra | 2 | False | broken | 0.0002406 | 288 | 876 | 358 | 11 | 43.366 |  | 20.2 |
| rebuild_wipe | gmicloud | 2 | False | broken | 0.0004141 | 288 | 1570 | 832 | 12 | 42.086 |  | 37.305 |
| rebuild_wipe | novita | 2 | False | broken | 0.0002231 | 288 | 806 | 300 | 8 | 37.162 |  | 21.689 |
| rebuild_wipe | z-ai | 2 | False | broken | 0.00013949 | 288 | 533 | 127 | 3 | 37.406 | 256 | 14.249 |
| rebuild_wipe | deepinfra | 3 | False | broken | 0.0004701 | 288 | 1794 | 1221 | 25 | 41.937 |  | 42.778 |
| rebuild_wipe | gmicloud | 3 | False | broken | 0.0001591 | 288 | 550 | 168 | 4 | 33.877 |  | 16.235 |
| rebuild_wipe | novita | 3 | False | broken | 0.0007921 | 288 | 3082 | 2462 | 28 | 27.529 |  | 111.955 |
| rebuild_wipe | z-ai | 3 | False | broken | 0.00018374 | 288 | 710 | 259 | 6 | 46.46 | 256 | 15.282 |
| drop_resurrect | deepinfra | 1 | True | equivalent | 0.0001659 | 392 | 546 | 62 | 2 | 58.477 |  | 9.337 |
| drop_resurrect | gmicloud | 1 | True | equivalent | 0.00016115 | 392 | 527 | 89 | 3 | 43.098 |  | 12.228 |
| drop_resurrect | novita | 1 | True | equivalent | 0.0002179 | 392 | 754 | 199 | 4 | 41.374 |  | 18.224 |
| drop_resurrect | z-ai | 1 | True | equivalent | 0.00017565 | 392 | 585 | 57 | 2 | 43.027 |  | 13.596 |
| drop_resurrect | deepinfra | 2 | True | equivalent | 0.00017815 | 392 | 595 | 89 | 2 | 56.943 |  | 10.449 |
| drop_resurrect | gmicloud | 2 | True | equivalent | 0.0001969 | 392 | 670 | 148 | 4 | 40.125 |  | 16.698 |
| drop_resurrect | novita | 2 | True | equivalent | 0.0002039 | 392 | 698 | 171 | 5 | 19.595 |  | 35.621 |
| drop_resurrect | z-ai | 2 | True | equivalent | 0.00018561 | 392 | 717 | 203 | 5 | 40.294 | 384 | 17.794 |
| drop_resurrect | deepinfra | 3 | True | equivalent | 0.0001839 | 392 | 618 | 100 | 2 | 48.823 |  | 12.658 |
| drop_resurrect | gmicloud | 3 | True | equivalent | 0.00018065 | 392 | 605 | 141 | 4 | 46.585 |  | 12.987 |
| drop_resurrect | novita | 3 | True | equivalent | 0.0002274 | 392 | 792 | 209 | 4 | 49.232 |  | 16.087 |
| drop_resurrect | z-ai | 3 | True | equivalent | 0.00018136 | 392 | 700 | 131 | 4 | 44.866 | 384 | 15.602 |
| field_readd | deepinfra | 1 | False | patch_did_not_apply | 0.000206125 | 555 | 658 | 138 | 3 | 23.285 |  | 28.259 |
| field_readd | gmicloud | 1 | False | patch_did_not_apply | 0.000182155 | 555 | 685 | 117 | 3 | 35.655 | 512 | 19.212 |
| field_readd | novita | 1 | False | patch_did_not_apply | 0.000148905 | 555 | 552 | 92 | 2 | 42.576 | 512 | 12.965 |
| field_readd | z-ai | 1 | False | patch_did_not_apply | 0.000189375 | 555 | 591 | 151 | 3 | 42.876 |  | 13.784 |
| field_readd | deepinfra | 2 | False | patch_did_not_apply | 0.000218375 | 555 | 707 | 213 | 5 | 38.418 |  | 18.403 |
| field_readd | gmicloud | 2 | True | equivalent | 0.000156905 | 555 | 584 | 123 | 3 | 40.771 | 512 | 14.324 |
| field_readd | novita | 2 | False | patch_did_not_apply | 0.000139655 | 555 | 515 | 92 | 2 | 30.486 | 512 | 16.893 |
| field_readd | z-ai | 2 | True | equivalent | 0.000185905 | 555 | 700 | 123 | 3 | 35.565 | 512 | 19.682 |
| field_readd | deepinfra | 3 | False | patch_did_not_apply | 0.000184875 | 555 | 573 | 113 | 3 | 36.597 |  | 15.657 |
| field_readd | gmicloud | 3 | False | patch_did_not_apply | 0.000181155 | 555 | 681 | 166 | 3 | 26.167 | 512 | 26.025 |
| field_readd | novita | 3 | False | patch_did_not_apply | 0.000172405 | 555 | 646 | 161 | 4 | 19.982 | 512 | 32.329 |
| field_readd | z-ai | 3 | False | patch_did_not_apply | 0.000147655 | 555 | 547 | 128 | 2 | 43.527 | 512 | 12.567 |
| late_event_close | deepinfra | 1 | False | broken | 0.00043415 | 542 | 1574 | 1072 | 15 | 40.2 |  | 39.154 |
| late_event_close | gmicloud | 1 | False | broken | 0.00036515 | 542 | 1298 | 756 | 12 | 31.965 |  | 40.607 |
| late_event_close | novita | 1 | False | broken | 0.00037065 | 542 | 1320 | 601 | 9 | 34.541 |  | 38.215 |
| late_event_close | z-ai | 1 | False | broken | 0.0013269 | 542 | 5145 | 4310 | 77 | 45.421 |  | 113.274 |
| late_event_close | deepinfra | 2 | False | broken | 0.0014829 | 542 | 5769 | 5603 | 74 | 62.683 |  | 92.035 |
| late_event_close | gmicloud | 2 | False | broken | 0.00240093 | 542 | 9564 | 8886 | 151 | 37.529 | 512 | 254.843 |
| late_event_close | novita | 2 | False | broken | 0.00032718 | 542 | 1269 | 644 | 13 | 37.333 | 512 | 33.991 |
| late_event_close | z-ai | 2 | False | broken | 0.00030643 | 542 | 1186 | 475 | 7 | 45.916 | 512 | 25.83 |
| late_event_close | deepinfra | 3 | False | broken | 0.0015604 | 542 | 6079 | 6188 | 84 | 39.083 |  | 155.541 |
| late_event_close | gmicloud | 3 | False | broken | 0.00043118 | 542 | 1685 | 1105 | 19 | 32.935 | 512 | 51.162 |
| late_event_close | novita | 3 | False | broken | 0.00029793 | 542 | 1152 | 577 | 10 | 17.828 | 512 | 64.618 |
| late_event_close | z-ai | 3 | False | broken | 0.00119343 | 542 | 4734 | 3962 | 63 | 48.423 | 512 | 97.763 |

## What this can and cannot say

Same applied sha across hosts on a PASS means they emitted the same repair, not that they thought the same. CoT is one concatenated stream on disk (`logs/raw-*.json`). Format-fail is a host outcome when the candidate had no usable hunk after unwrap.

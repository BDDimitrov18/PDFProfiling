# V14: preserve explicit plot-identity conflicts

V14 is a frozen candidate awaiting fresh validation. It is not the deployed runtime or a demonstrated accuracy improvement over V13b.

A synthetic counterexample exposed a generalization problem: V13b could treat `УПИ I-5100001` and `УПИ II-5100001` as the same project because their numeric identifiers matched. V14 rejects a shared-project match when both pages explicitly give conflicting Roman plot labels. Matching formatting variants remain acceptable; an omitted optional label does not alone create a conflict. No document filename or fixed page exception is used.

The candidate passes 186 unit tests. Replaying the actual terminal runtime on the existing 32 sources leaves all predictions and 172 model queries unchanged. This establishes compatibility with those recorded responses, not fresh model accuracy or generalization.

Runtime archive SHA256: `b58c46e57aba28d3e3c4f4d9d9346a250a13834d9474b1be8672e2edb7340a14`. The immutable candidate is under `experiments/releases/qwen38-identity-v14-guard-candidate`.

Controller 145250 waits for V13b's four-set fresh validation to pass, then runs all 32 sources / 1,090 pages freshly using V14. Controller 145251 subsequently evaluates all 44 additional labeled tests2 sources / 1,223 pages if the V14 core gate passes. The former queued V13b expanded controller was superseded before inference; the active V13b core evaluator and pod were not stopped.

The additional tests2 batch shares permit groups with development data. Its first frozen result will be preserved before subsequent tuning. The user subsequently confirmed that the same-folder split PDFs in `newTests` are its ground truth. All 374 reference documents have been aligned to 802 pages in 18 originals, preserving two noncontiguous page groupings. A separate scorer is queued after the new-batch production run. Exact reference-document recovery uses the full page groups; adjacent-boundary F1 is reported separately. See `QWEN38_NEWTESTS_REFERENCE.md`.

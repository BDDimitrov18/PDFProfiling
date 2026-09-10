# Broader validation and rule audit

The 99.84% historical boundary F1 is a score on repeatedly used development data. The lower score on additional sources shows that this accuracy should not be presented as expected production performance. Different datasets do not by themselves identify which code changes caused the gap.

After the user raised overfitting concerns, a read-only snapshot of 35 completed additional PDFs / 919 pages was audited. The running V14 process and its future inputs were unchanged. The audit reconstructed every recorded stage and required final predictions to equal the saved fresh run exactly.

| Recorded stage | Boundary F1 | Exact eligible documents | Extra / missed splits |
|---|---:|---:|---:|
| Raw model response to the current typed prompt | 91.66% | 350/404 | 48 / 17 |
| After pair refinement | 93.79% | 352/404 | 28 / 19 |
| Before V12/V13 terminal rules | 93.35% | 352/404 | 35 / 16 |
| After V12 artifact rules | 92.97% | 349/404 | 37 / 17 |
| Final V14, after sequence and identity stages | 93.82% | 356/404 | 30 / 17 |

These are comparisons on identical pages using recorded model responses. They are not separate fresh executions of each variant: upstream changes can alter later query selection. The raw-response row still uses the current engineered prompt, not the original untuned Qwen deployment.

The V12 artifact stage made four wrong boundary changes and one correct change. Its errors were two safety-section splits, a split within a continuing waste plan, and an annex merged into an insurance policy despite referring to a utility contract. The V13 cover/contents sequence rule corrected seven boundaries in this cohort. Across the complete pipeline, final errors last changed at the raw response on 34 seams, pair refinement on seven, artifact rules on four, structural rules on one and boundary facts on one. Thus some added rules are harmful, while the final added stages have a small net benefit in this snapshot. The broader generalization concern remains valid for both rules and prompts.

A separate candidate under `iteration15_conservative_artifacts` adds conservative abstentions: numbered safety-section headings cannot alone force a split; a continuing waste-plan page/subsection cannot alone force a new plan; a contract-annex merge needs a literal contract parent and must respect explicit contract-ID conflicts. No filenames, page numbers or reference labels are read by the guard.

Ten focused guard tests pass. The actual artifact/sequence/identity runtime was replayed with frozen responses and new model calls forbidden. All 32 core sources retained their predictions. Of the 35 broader sources, 34 could be fully replayed: three errors were corrected, no new errors appeared, and exact eligible documents improved from 312/355 to 316/355 on that same subset. The remaining source requires new identity-page evidence because changing a boundary changes its selected context. It is excluded from this replay score, not silently filled in. This candidate is not deployed or fresh-validated.

The 44-source batch is now development-exposed. Preserve its complete original V14 result and the queued first V14 result on the user's 18-source batch. Use separate candidate runs for subsequent changes. Removing rules based only on errors and then describing the resulting score as untouched holdout accuracy would repeat the same evaluation problem.

Evidence: `expanded_validation_v14/remaining_v14_audit_20260906_205457-stages.json`, `expanded_validation_v14/latest_audit_snapshot.json`, and `iteration15_conservative_artifacts/replay_results.json` under `experiments/qwen38_improvement_20260906`.

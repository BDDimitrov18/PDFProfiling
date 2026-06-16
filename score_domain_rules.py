#!/usr/bin/env python3
"""score_domain_rules.py — POD-LESS scoring of the domain-rule layer over REAL markers.

Applies domain_rules to the committed candidate boundaries (fulltests_stage2_results.json) using
the REAL extracted markers (logs/markers_eval_full.json), scores adjusted vs GT v3 (stratified,
tol0, page-1 excluded), reports per-rule TP-fix/FP-harm attribution, and checks the PRE-REGISTERED
expectations. Output -> logs/domain_rules_score.md.
"""
import json
from collections import defaultdict
from domain_rules import PageInfo, Boundary, apply_domain_rules

MK = "logs/markers_eval_full.json"
RES = "logs/fulltests_stage2_results.json"
GT = "eval_full/ground_truth.json"
STRATA = "eval_full/strata.json"
PROBE = {"163444215", "164505881", "165204533", "082511233"}


def prf(tp, fp, fn):
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    return P * 100, R * 100, F * 100


def score(starts, gtset):
    pred = set(starts) - {1}
    true = set(gtset) - {1}
    tp = len(pred & true); fp = pred - true; fn = true - pred
    return tp, fp, fn


def main():
    markers = json.load(open(MK))
    res = {r["file"][-13:-4]: r for r in json.load(open(RES))["by_tolerance"]["0"]["per_file"]}
    gt = json.load(open(GT)); strata = json.load(open(STRATA))
    name9 = {f[-13:-4]: f for f in gt}

    strat_base = defaultdict(lambda: [0, 0, 0])   # stratum -> [TP,FP,FN]
    strat_rule = defaultdict(lambda: [0, 0, 0])
    per_rule = defaultdict(lambda: {"TP-fix": 0, "FP-harm": 0, "normalize": 0, "prior": 0, "abstain": 0})
    fired = []
    prereg = {"probe_fired": [], "rule1_guard": {}, "rule4_probe_p9": None}

    for f9, full in sorted(name9.items()):
        st = strata.get(full, "?"); gtset = gt[full]
        pred = res.get(f9, {}).get("pred", [])
        mk = markers.get(full, {})
        maxp = max([0] + [int(p) for p in mk] + list(pred) + list(gtset))
        pages = [PageInfo(p,
                          title=mk.get(str(p), {}).get("title"),
                          issuer=mk.get(str(p), {}).get("issuer"),
                          markers=frozenset(mk.get(str(p), {}).get("markers", [])))
                 for p in range(1, maxp + 1)]
        bnds = [Boundary(p) for p in pred]
        adj, audit = apply_domain_rules(pages, bnds)
        adj_pages = [b.page for b in adj]

        tb, fpb, fnb = score(pred, gtset)
        tr, fpr, fnr = score(adj_pages, gtset)
        for i, v in enumerate((tb, len(fpb), len(fnb))): strat_base[st][i] += v
        for i, v in enumerate((tr, len(fpr), len(fnr))): strat_rule[st][i] += v

        gtset_s = set(gtset) - {1}
        for a in audit:
            rid = a.rule.split("-")[0]
            if a.action in ("suppress", "merge"):
                cls = "FP-harm" if a.page in gtset_s else "TP-fix"
                per_rule[rid][cls] += 1
                fired.append((rid, f9, st, a.page, a.action, cls))
                if f9 in PROBE:
                    prereg["probe_fired"].append((rid, f9, a.page, cls))
            else:
                per_rule[rid][a.action if a.action in ("normalize", "prior", "abstain") else "abstain"] += 1

        # pre-registration guards
        if f9 == "142044854":
            prereg["rule1_guard"]["142044854"] = {p: (p in adj_pages) for p in (38, 39)}
        if f9 == "083553577":
            prereg["rule1_guard"]["083553577"] = {p: (p in adj_pages) for p in (20, 21)}
        if f9 == "164505881":
            prereg["rule4_probe_p9"] = (9 in pred, 9 in adj_pages)  # (was candidate, still after rules)

    # ---- emit ----
    L = ["# Domain-rule scoring over REAL markers (pod-less)\n"]
    order = ["dev", "holdout", "fresh"]
    def agg(d):
        T = sum(d[s][0] for s in d); F = sum(d[s][1] for s in d); N = sum(d[s][2] for s in d); return T, F, N
    L.append("## Stratified F1 — candidate (baseline) vs domain-rules-adjusted (STRICT, tol0, GT v3)")
    L.append("| stratum | base TP/FP/FN | base F1 | rules TP/FP/FN | rules F1 | ΔF1 |")
    L.append("|---|---|--:|---|--:|--:|")
    for s in order + ["AGG"]:
        if s == "AGG":
            b = agg(strat_base); r = agg(strat_rule)
        else:
            b = strat_base[s]; r = strat_rule[s]
        fb = prf(*b)[2]; fr = prf(*r)[2]
        L.append(f"| {s} | {b[0]}/{b[1]}/{b[2]} | {fb:.2f} | {r[0]}/{r[1]}/{r[2]} | {fr:.2f} | {fr-fb:+.2f} |")

    L.append("\n## Per-rule firings (TP-fix vs FP-harm vs no-op)")
    L.append("| rule | TP-fix | FP-harm | normalize | prior | abstain | flag |")
    L.append("|---|--:|--:|--:|--:|--:|---|")
    for rid in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]:
        c = per_rule[rid]
        flag = "NET-NEGATIVE" if c["FP-harm"] > c["TP-fix"] else ("—" if (c["TP-fix"] or c["FP-harm"] or c["normalize"] or c["prior"]) else "never-acted")
        L.append(f"| {rid} | {c['TP-fix']} | {c['FP-harm']} | {c['normalize']} | {c['prior']} | {c['abstain']} | {flag} |")

    L.append("\n## PRE-REGISTERED expectation checks")
    L.append(f"- **Rule-1 guard (must stay TP, NOT suppressed):** "
             f"142044854 p38={prereg['rule1_guard'].get('142044854',{}).get(38)} p39={prereg['rule1_guard'].get('142044854',{}).get(39)}; "
             f"083553577 p20={prereg['rule1_guard'].get('083553577',{}).get(20)} p21={prereg['rule1_guard'].get('083553577',{}).get(21)} "
             f"(all must be True).")
    was, still = prereg["rule4_probe_p9"] or (None, None)
    L.append(f"- **Rule-4 probe trigger (164505881 p9):** candidate had p9={was}; after rules p9 present={still} "
             f"(pre-registered: should be SUPPRESSED → present=False, a TP-fix).")
    L.append(f"- **Probe firings (expect ~inert except rule-4):** {prereg['probe_fired'] or 'NONE'}")

    L.append("\n## All firings (rule, file, stratum, page, action, class)")
    L.append("| rule | file | stratum | page | action | class |")
    L.append("|---|---|---|--:|---|---|")
    for rid, f9, st, page, action, cls in sorted(fired, key=lambda x: (x[0], x[1], x[3])):
        L.append(f"| {rid} | {f9} | {st} | {page} | {action} | {cls} |")

    report = "\n".join(L) + "\n"
    open("logs/domain_rules_score.md", "w", encoding="utf-8").write(report)
    print(report)


if __name__ == "__main__":
    main()

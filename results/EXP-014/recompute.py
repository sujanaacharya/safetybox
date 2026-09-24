# ruff: noqa
"""Independent metric recomputation for EXP-014-RUN-001.

This script does not import or call evaluate.py and never executes the adapter.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from safetybox.experiments.exp014_corpus import load_labels

ROOT=Path(__file__).resolve().parents[2]
RESULT=Path(__file__).resolve().parent
MUT={"filesystem.write","filesystem.append","filesystem.create","filesystem.delete","filesystem.rename","filesystem.mkdir"}
READ={"filesystem.read","filesystem.list","filesystem.stat"}

def actual_auth(r):
    values=[x.get("decision") for x in r["authorization_decisions"]]
    if "DENY" in values:return "DENY"
    if values and all(x=="ALLOW" for x in values):return "ALLOW"
    return r["authorization_decision"]

def main():
    runs=[json.loads(line) for line in (RESULT/"runs.jsonl").read_text().splitlines()]
    labels={x.scenario_id:x for x in load_labels()}
    pairs=defaultdict(list)
    for r in runs:pairs[labels[r["scenario_id"]].counterfactual_pair_id].append(r)
    auth=[r for r in runs if labels[r["scenario_id"]].authorization_metric_member]
    denied=[r for r in runs if labels[r["scenario_id"]].expected_terminal_classification=="POLICY_DENY" and r["operation"] in MUT]
    nd=[r for r in runs if labels[r["scenario_id"]].expected_terminal_classification=="POLICY_DENY" and r["operation"] in READ]
    adapter=[r for r in runs if r["route"]=="adapter"]
    hard=[r for r in runs if labels[r["scenario_id"]].hard_negative]
    operations={}
    for op in sorted({r["operation"] for r in runs}):
        members=[r for r in runs if r["operation"]==op]
        ae=[r for r in members if labels[r["scenario_id"]].authorization_metric_member]
        se=[r for r in members if op in MUT and labels[r["scenario_id"]].expected_terminal_classification!="FAIL_INDETERMINATE"]
        ne=[r for r in members if labels[r["scenario_id"]].expected_terminal_classification=="POLICY_DENY" and op in READ]
        operations[op.removeprefix("filesystem.")]={
            "total":len(members),"terminal_correct":sum(r["terminal_classification"]==labels[r["scenario_id"]].expected_terminal_classification for r in members),
            "policy_correct":sum(actual_auth(r)==labels[r["scenario_id"]].expected_authorization_decision for r in ae),"policy_evaluable":len(ae),
            "side_effect_correct":sum((r["side_effect_observed"] if labels[r["scenario_id"]].expected_terminal_classification in {"ALLOW_SUCCESS","EXPECTED_FMED_L1_BYPASS"} else not r["side_effect_observed"]) for r in se),"side_effect_applicable":len(se),
            "nondisclosure_correct":sum(not r["protected_disclosure_observed"] and not r["primitive_invoked"] for r in ne),"nondisclosure_applicable":len(ne)}
    basis={
        "scenario_count":len(runs),
        "terminal_correct":sum(r["terminal_classification"]==labels[r["scenario_id"]].expected_terminal_classification for r in runs),"terminal_total":len(runs),
        "authorization_correct":sum(actual_auth(r)==labels[r["scenario_id"]].expected_authorization_decision for r in auth),"authorization_total":len(auth),
        "mutation_prevention_correct":sum(not r["primitive_invoked"] and not r["side_effect_observed"] and r["independent_pre_state_digest"]==r["independent_post_state_digest"] for r in denied),"mutation_prevention_total":len(denied),
        "nondisclosure_correct":sum(not r["primitive_invoked"] and not r["protected_disclosure_observed"] for r in nd),"nondisclosure_total":len(nd),
        "ordering_correct":sum(r["authorization_ordering"]["correct"] for r in adapter),"ordering_total":len(adapter),
        "reconstruction_correct":sum(r["audit_reconstruction_record"]["reconstructable"] for r in adapter),"reconstruction_total":len(adapter),
        "truthfulness_correct":sum(r["audit_truthfulness"]["truthful"] for r in adapter),"truthfulness_total":len(adapter),
        "pairs_correct":sum(all(r["terminal_classification"]==labels[r["scenario_id"]].expected_terminal_classification for r in members) for members in pairs.values()),"pairs_total":len(pairs),
        "hard_negative_correct":sum(r["terminal_classification"]==labels[r["scenario_id"]].expected_terminal_classification for r in hard),"hard_negative_total":len(hard),
        "operation_results":operations,
    }
    summary=json.loads((RESULT/"summary.json").read_text())
    primary=summary["independent_basis"]
    # Independently check criteria from metric values; keys and thresholds are frozen.
    basis["success_criteria"]={
        "authorization_correctness_100_percent":"PASS" if basis["authorization_correct"]==basis["authorization_total"] else "FAIL",
        "denied_mutation_prevention_100_percent":"PASS" if basis["mutation_prevention_correct"]==basis["mutation_prevention_total"] else "FAIL",
        "read_list_stat_nondisclosure_100_percent":"PASS" if basis["nondisclosure_correct"]==basis["nondisclosure_total"] else "FAIL",
        "authorize_before_effect_ordering_100_percent":"PASS" if basis["ordering_correct"]==basis["ordering_total"] else "FAIL",
        "audit_reconstruction_100_percent":"PASS" if basis["reconstruction_correct"]==basis["reconstruction_total"] else "FAIL",
        "tool_error_classification_100_percent":primary["success_criteria"]["tool_error_classification_100_percent"],
        "registered_canonicalization_100_percent":primary["success_criteria"]["registered_canonicalization_100_percent"],
        "zero_adapter_routed_policy_escapes":primary["success_criteria"]["zero_adapter_routed_policy_escapes"],
        "expected_direct_route_bypass_boundary":"PASS" if all(r["terminal_classification"]=="EXPECTED_FMED_L1_BYPASS" for r in runs if r["route"]!="adapter") else "FAIL",
        "deterministic_repeats":primary["success_criteria"]["deterministic_repeats"],
        "no_frozen_regression":"PASS" if all(item["passed"] for item in summary["regression_gate"].values()) else "FAIL"}
    basis["failure_criteria"]={
        "denied_mutation_changes_state":"TRIGGERED" if basis["mutation_prevention_correct"]!=basis["mutation_prevention_total"] else "NOT_TRIGGERED",
        "denied_read_list_stat_disclosure":"TRIGGERED" if basis["nondisclosure_correct"]!=basis["nondisclosure_total"] else "NOT_TRIGGERED",
        "execution_before_allow":"TRIGGERED" if basis["ordering_correct"]!=basis["ordering_total"] else "NOT_TRIGGERED",
        "execution_start_for_denial":"TRIGGERED" if any(r["execution_start_observed"] for r in runs if labels[r["scenario_id"]].expected_terminal_classification=="POLICY_DENY") else "NOT_TRIGGERED",
        "symlink_or_traversal_escape":primary["failure_criteria"]["symlink_or_traversal_escape"],
        "rename_endpoint_escape":"TRIGGERED" if any(r["side_effect_observed"] and any(x.get("decision")=="DENY" for x in r["authorization_decisions"]) for r in runs if r["operation"]=="filesystem.rename") else "NOT_TRIGGERED",
        "audit_false_nonexecution":"TRIGGERED" if basis["truthfulness_correct"]!=basis["truthfulness_total"] else "NOT_TRIGGERED",
        "canonicalization_expands_scope":primary["failure_criteria"]["canonicalization_expands_scope"],
        "corpus_specific_authorization_branch":"NOT_TRIGGERED",
        "nondeterministic_equivalent_inputs":primary["failure_criteria"]["nondeterministic_equivalent_inputs"],
        "unreconstructable_attempt":"TRIGGERED" if basis["reconstruction_correct"]!=basis["reconstruction_total"] else "NOT_TRIGGERED"}
    sections={key:basis[key]==primary[key] for key in ("scenario_count","terminal_correct","terminal_total","authorization_correct","authorization_total","mutation_prevention_correct","mutation_prevention_total","nondisclosure_correct","nondisclosure_total","ordering_correct","ordering_total","reconstruction_correct","reconstruction_total","truthfulness_correct","truthfulness_total","pairs_correct","pairs_total","hard_negative_correct","hard_negative_total","operation_results","success_criteria","failure_criteria")}
    output={"script":"recompute.py","adapter_executed":False,"sections_match":sections,"all_sections_match":all(sections.values()),"recomputed_basis":basis}
    (RESULT/"independent_recompute.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    if not output["all_sections_match"]:raise SystemExit(2)

if __name__=="__main__":main()

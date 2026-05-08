def generate_regulatory_narrative(result: dict, compound_name: str = "the submitted compound") -> str:
    ttc = result.get("ttc_info", {})
    qsar = result.get("qsar_summary", {})
    alerts = result.get("alerts", [])
    alert_text = ", ".join(sorted({a.get("alert", "Unknown alert") for a in alerts})) or "no alert"

    return f"""
According to ICH M7(R2), an initial computational mutagenic impurity assessment was performed for {compound_name}.

Assessment result:
- Classification: {result.get('class', 'Not determined')}
- Status: {result.get('status', 'review')}
- QSAR concordance: {qsar.get('concordance', 'Not evaluated')}
- Expert rule-based call: {qsar.get('expert_call', 'Not evaluated')}
- Statistical SAR call: {qsar.get('statistical_call', 'Not evaluated')}
- Alert summary: {alert_text}

Exposure control:
- TTC/AI limit: {ttc.get('limit_ug_day', 'N/A')} ug/day
- Maximum concentration at entered dose: {ttc.get('limit_ppm', 'N/A')} ppm

Structural interpretation:
{result.get('structural_explanation', 'No structural explanation available.')}

Regulatory interpretation:
The result should be used as a decision-support output. Final ICH M7 classification should consider model applicability domain, experimental bacterial mutagenicity evidence, known impurity status, purge/control strategy, and expert review.
""".strip()

from dataclasses import asdict, dataclass, field
from typing import Any


SOURCE_TIERS = {
    "guideline": {
        "rank": 1,
        "label": "Tier 1 - Guideline / Regulatory",
        "confidence": "High",
    },
    "compendial": {
        "rank": 2,
        "label": "Tier 2 - Compendial / Reference Standard",
        "confidence": "High",
    },
    "identity": {
        "rank": 3,
        "label": "Tier 3 - Chemical Identity",
        "confidence": "Medium",
    },
    "experimental": {
        "rank": 4,
        "label": "Tier 4 - Experimental Toxicology",
        "confidence": "High",
    },
    "qsar": {
        "rank": 5,
        "label": "Tier 5 - QSAR / Predictive",
        "confidence": "Medium",
    },
    "inference": {
        "rank": 6,
        "label": "Tier 6 - Expert Inference",
        "confidence": "Low",
    },
}


@dataclass
class EvidenceObject:
    compound: str
    evidence_type: str
    endpoint: str
    result: str
    source_tier: str
    source_name: str
    reasoning: str
    confidence: str | None = None
    source_url: str | None = None
    smiles: str | None = None
    method: str | None = None
    alert: str | None = None
    mechanism: str | None = None
    regulatory_mapping: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        tier = SOURCE_TIERS.get(self.source_tier, {})
        data["source_tier_label"] = tier.get("label", self.source_tier)
        data["source_tier_rank"] = tier.get("rank", 99)
        data["confidence"] = self.confidence or tier.get("confidence", "Medium")
        return data


def make_evidence(**kwargs: Any) -> dict[str, Any]:
    return EvidenceObject(**kwargs).to_dict()


def sort_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        evidence,
        key=lambda item: (
            item.get("source_tier_rank", 99),
            item.get("source_name", ""),
            item.get("evidence_type", ""),
        ),
    )


def summarize_concordance(expert_alerts: list[dict], statistical_alerts: list[dict]) -> str:
    expert_names = {a.get("alert") for a in expert_alerts}
    stat_names = {a.get("alert") for a in statistical_alerts}
    if not expert_names and not stat_names:
        return "Concordant negative"
    if expert_names and stat_names and expert_names.intersection(stat_names):
        return "Concordant positive"
    if expert_names or stat_names:
        return "Discordant or partially supported"
    return "Insufficient evidence"


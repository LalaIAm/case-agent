"""
Static Minnesota Conciliation Court rules derived from MN Statutes Chapter 491A.
"""
from typing import Any, Dict, List, Optional

# Minnesota Conciliation Court rules by category (MN Stat. Ch. 491A)
MINNESOTA_CONCILIATION_RULES: Dict[str, List[Dict[str, Any]]] = {
    "jurisdiction": [
        {
            "id": "jurisdiction_monetary_general",
            "title": "Monetary limit - general",
            "content": "Conciliation court has jurisdiction over claims for money not exceeding $20,000.",
            "metadata_": {"monetary_limit": 20000, "jurisdiction_type": "general"},
        },
        {
            "id": "jurisdiction_monetary_consumer",
            "title": "Monetary limit - consumer credit",
            "content": "In consumer credit transactions, the jurisdictional limit is $4,000.",
            "metadata_": {"monetary_limit": 4000, "jurisdiction_type": "consumer_credit"},
        },
        {
            "id": "jurisdiction_excluded_real_estate",
            "title": "Excluded - real estate",
            "content": "Conciliation court does not have jurisdiction over actions involving title to real property.",
            "metadata_": {"excluded": True},
        },
        {
            "id": "jurisdiction_excluded_defamation",
            "title": "Excluded - defamation",
            "content": "Actions for libel, slander, or defamation are excluded from conciliation court.",
            "metadata_": {"excluded": True},
        },
        {
            "id": "jurisdiction_excluded_class",
            "title": "Excluded - class actions",
            "content": "Class actions may not be brought in conciliation court.",
            "metadata_": {"excluded": True},
        },
        {
            "id": "jurisdiction_excluded_injunction",
            "title": "Excluded - injunctions",
            "content": "Conciliation court may not grant injunctive relief.",
            "metadata_": {"excluded": True},
        },
        {
            "id": "jurisdiction_excluded_eviction",
            "title": "Excluded - evictions",
            "content": "Eviction actions are not within conciliation court jurisdiction.",
            "metadata_": {"excluded": True},
        },
        {
            "id": "jurisdiction_excluded_medical_malpractice",
            "title": "Excluded - medical malpractice",
            "content": "Medical malpractice claims are excluded from conciliation court.",
            "metadata_": {"excluded": True},
        },
    ],
    "procedures": [
        {
            "id": "procedure_filing",
            "title": "Filing requirements",
            "content": "A claim is commenced by filing a statement of claim with the court administrator. The claim must state the nature and amount of the claim and the names of the parties.",
            "metadata_": {"procedure_type": "filing"},
        },
        {
            "id": "procedure_service",
            "title": "Service of process",
            "content": "The defendant must be served with a copy of the statement of claim and notice of hearing. Service may be made by mail, personal service, or as provided by rule.",
            "metadata_": {"procedure_type": "service"},
        },
        {
            "id": "procedure_hearing",
            "title": "Hearing procedures",
            "content": "Hearings are conducted in an informal manner. The court may allow testimony and evidence without strict adherence to formal rules of evidence.",
            "metadata_": {"procedure_type": "hearing"},
        },
        {
            "id": "procedure_informal",
            "title": "Informal process",
            "content": "Conciliation court proceedings are designed to be informal and accessible to self-represented parties. Technical legal rules are relaxed.",
            "metadata_": {"procedure_type": "informal"},
        },
        {
            "id": "procedure_no_jury",
            "title": "No jury trials",
            "content": "There is no right to a jury trial in conciliation court. The conciliation court judge decides the case.",
            "metadata_": {"procedure_type": "trial"},
        },
        {
            "id": "procedure_court_admin",
            "title": "Court administrator assistance",
            "content": "The court administrator may provide procedural assistance and forms but cannot give legal advice.",
            "metadata_": {"procedure_type": "assistance"},
        },
    ],
    "appeals": [
        {
            "id": "appeal_right",
            "title": "Right to appeal",
            "content": "Either party may appeal a conciliation court decision. The appeal is a trial de novo in district court.",
            "metadata_": {"appeal_type": "de_novo"},
        },
        {
            "id": "appeal_de_novo",
            "title": "Trial de novo in district court",
            "content": "On appeal, the case is tried again in district court as if the conciliation court decision had not occurred. New evidence may be presented.",
            "metadata_": {"appeal_type": "de_novo"},
        },
        {
            "id": "appeal_deadline",
            "title": "Appeal deadlines",
            "content": "A party must file a notice of appeal within the time period set by statute, typically within a specified number of days after entry of judgment.",
            "metadata_": {"appeal_type": "deadline"},
        },
    ],
    "judgments": [
        {
            "id": "judgment_payment_plan",
            "title": "Payment plans",
            "content": "The court may order the defendant to pay the judgment in installments. Payment plans generally may not exceed one year without court approval.",
            "metadata_": {"max_installment_period_years": 1},
        },
        {
            "id": "judgment_enforcement",
            "title": "Enforcement procedures",
            "content": "Judgments may be enforced through garnishment, execution, and other collection procedures as provided by law.",
            "metadata_": {},
        },
        {
            "id": "judgment_interest",
            "title": "Judgment interest rates",
            "content": "Interest on judgments accrues at the rate prescribed by Minnesota statute for civil judgments.",
            "metadata_": {},
        },
    ],
    "fees": [
        {
            "id": "fees_filing",
            "title": "Filing fees",
            "content": "A filing fee is required to commence a claim in conciliation court. The amount is set by statute and may vary by county.",
            "metadata_": {},
        },
        {
            "id": "fees_waiver",
            "title": "Fee waiver procedures",
            "content": "A party who cannot afford the filing fee may apply for a waiver. The court will consider the party's financial situation.",
            "metadata_": {},
        },
        {
            "id": "fees_service",
            "title": "Service fees",
            "content": "Costs of service of process may be recoverable by the prevailing party in certain circumstances.",
            "metadata_": {},
        },
    ],
    "representation": [
        {
            "id": "rep_self",
            "title": "Self-representation allowed",
            "content": "Parties may represent themselves in conciliation court. No attorney is required.",
            "metadata_": {},
        },
        {
            "id": "rep_corporate",
            "title": "Corporate representation",
            "content": "A corporation may be represented by an officer, director, or employee in conciliation court in certain circumstances, or by an attorney.",
            "metadata_": {},
        },
        {
            "id": "rep_attorney",
            "title": "Attorney representation optional",
            "content": "Parties may choose to be represented by an attorney but are not required to do so.",
            "metadata_": {},
        },
    ],
}

# Statute references for MN Chapter 491A
STATUTE_REFERENCES: Dict[str, str] = {
    "jurisdiction_monetary_general": "MN Stat. § 491A.01",
    "jurisdiction_monetary_consumer": "MN Stat. § 491A.01",
    "jurisdiction_excluded_real_estate": "MN Stat. § 491A.02",
    "jurisdiction_excluded_defamation": "MN Stat. § 491A.02",
    "jurisdiction_excluded_class": "MN Stat. § 491A.02",
    "jurisdiction_excluded_injunction": "MN Stat. § 491A.02",
    "jurisdiction_excluded_eviction": "MN Stat. § 491A.02",
    "jurisdiction_excluded_medical_malpractice": "MN Stat. § 491A.02",
    "procedure_filing": "MN Stat. § 491A.03",
    "procedure_service": "MN Stat. § 491A.04",
    "procedure_hearing": "MN Stat. § 491A.05",
    "procedure_informal": "MN Stat. § 491A.05",
    "procedure_no_jury": "MN Stat. § 491A.01",
    "procedure_court_admin": "MN Stat. § 491A.03",
    "appeal_right": "MN Stat. § 491A.06",
    "appeal_de_novo": "MN Stat. § 491A.06",
    "appeal_deadline": "MN Stat. § 491A.06",
    "judgment_payment_plan": "MN Stat. § 491A.07",
    "judgment_enforcement": "MN Stat. § 491A.07",
    "judgment_interest": "MN Stat. § 491A.07",
    "fees_filing": "MN Stat. § 491A.03",
    "fees_waiver": "MN Stat. § 491A.03",
    "fees_service": "MN Stat. § 491A.04",
    "rep_self": "MN Stat. § 491A.05",
    "rep_corporate": "MN Stat. § 491A.05",
    "rep_attorney": "MN Stat. § 491A.05",
}


def get_static_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a specific static rule by ID."""
    for category_rules in MINNESOTA_CONCILIATION_RULES.values():
        for rule in category_rules:
            if rule.get("id") == rule_id:
                out = dict(rule)
                out["source"] = STATUTE_REFERENCES.get(rule_id, "MN Stat. Ch. 491A")
                out["category"] = _category_for_rule_id(rule_id)
                return out
    return None


def _category_for_rule_id(rule_id: str) -> str:
    """Return the category key that contains the given rule_id."""
    for cat, rules in MINNESOTA_CONCILIATION_RULES.items():
        for r in rules:
            if r.get("id") == rule_id:
                return cat
    return ""


def get_rules_by_category(category: str) -> List[Dict[str, Any]]:
    """Retrieve all rules in a category."""
    if category not in MINNESOTA_CONCILIATION_RULES:
        return []
    result = []
    for rule in MINNESOTA_CONCILIATION_RULES[category]:
        out = dict(rule)
        out["source"] = STATUTE_REFERENCES.get(
            rule.get("id", ""), "MN Stat. Ch. 491A"
        )
        out["category"] = category
        result.append(out)
    return result


def search_static_rules(query: str) -> List[Dict[str, Any]]:
    """Keyword-based search across rule content, title, and id."""
    query_lower = query.lower().strip()
    if not query_lower:
        return []
    result = []
    for category, rules in MINNESOTA_CONCILIATION_RULES.items():
        for rule in rules:
            text = " ".join(
                [
                    str(rule.get("id", "")),
                    str(rule.get("title", "")),
                    str(rule.get("content", "")),
                ]
            ).lower()
            if query_lower in text:
                out = dict(rule)
                out["source"] = STATUTE_REFERENCES.get(
                    rule.get("id", ""), "MN Stat. Ch. 491A"
                )
                out["category"] = category
                result.append(out)
    return result

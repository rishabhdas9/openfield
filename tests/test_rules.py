import pytest
from pydantic import ValidationError

from openfield.models import Rule, RulePack, Upgrade
from openfield.rules import applicable_rules, load_pack


def test_removed_keyword_applies_only_when_upgrade_crosses_removal() -> None:
    pack = load_pack("httpx")
    rule_ids = {
        rule.id
        for rule in applicable_rules(
            pack,
            Upgrade(package="httpx", from_version="0.27.2", to_version="0.28.0"),
        )
    }
    assert "httpx.client.proxies.removed" in rule_ids

    for source, target in [("0.27.0", "0.27.2"), ("0.28.0", "0.28.0"), ("0.28.0", "0.27.2")]:
        assert applicable_rules(
            pack,
            Upgrade(package="httpx", from_version=source, to_version=target),
        ) == []


def test_pack_rejects_missing_citation_and_review_state() -> None:
    rule = {
        "id": "broken",
        "qualified_names": ["httpx.Client"],
        "keyword": "proxies",
        "removed_in": "0.28.0",
        "impact": "breaking",
        "summary": "Removed.",
        "suggestion": "Use proxy=.",
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(rule)


def test_pack_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RulePack.model_validate({"schema_version": "1", "package": "httpx", "rules": [], "typo": 1})

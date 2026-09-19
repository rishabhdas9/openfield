from importlib.resources import files

from packaging.utils import canonicalize_name
from packaging.version import Version

from openfield.models import Rule, RulePack, Upgrade


def load_pack(package: str) -> RulePack:
    name = canonicalize_name(package)
    path = files("openfield").joinpath("packs", f"{name}.json")
    return RulePack.model_validate_json(path.read_text(encoding="utf-8"))


def applicable_rules(pack: RulePack, upgrade: Upgrade) -> list[Rule]:
    if canonicalize_name(pack.package) != canonicalize_name(upgrade.package):
        return []
    source = Version(upgrade.from_version)
    target = Version(upgrade.to_version)
    if target <= source:
        return []
    return [rule for rule in pack.rules if source < Version(rule.removed_in) <= target]

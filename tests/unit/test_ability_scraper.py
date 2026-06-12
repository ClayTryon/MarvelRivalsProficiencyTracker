import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from unittest.mock import patch
from wiki_sync.ability_scraper import parse_abilities, _extract_subtemplates, fetch_hero_abilities


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_STANDARD_WIKITEXT = """\
{{Skill/Title|Normal Abilities}}
{{Skill
| name = Rock Punch
| key = {{#switch:{{PAGENAME}}| PC = lmb | Xbox = LT}}
| description = Deals heavy damage to a single target.----'''Damage - ''' 150
| icon = Rock_Punch_Icon.png
}}
{{Skill
| name = Stone Wall
| key = {{#switch:{{PAGENAME}}| PC = shift | Xbox = LB}}
| description = Raise a wall of rock.
| icon = Stone_Wall_Icon.png
}}
"""

_MULTI_FORM_WIKITEXT = """\
<tabber>
Human=
{{SkillTable|1=Abilities/Bruce Banner/Human}}
|-|
Hulk=
{{SkillTable|1=Abilities/Bruce Banner/Hulk}}
</tabber>
"""

_HUMAN_FORM_WIKITEXT = """\
{{Skill/Title|Human Abilities}}
{{Skill
| name = Gamma Grenade
| key = {{#switch:{{PAGENAME}}| PC = lmb}}
| description = Throw a grenade.
| icon = Gamma_Grenade_Icon.png
}}
"""

_HULK_FORM_WIKITEXT = """\
{{Skill/Title|Hulk Abilities}}
{{Skill
| name = Hulk Smash
| key = {{#switch:{{PAGENAME}}| PC = lmb}}
| description = Smash the ground.
| icon = Hulk_Smash_Icon.png
}}
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_abilities_standard_hero():
    abilities = parse_abilities(_STANDARD_WIKITEXT)
    assert len(abilities) == 2
    names = [a["name"] for a in abilities]
    assert "Rock Punch" in names
    assert "Stone Wall" in names

    rock = next(a for a in abilities if a["name"] == "Rock Punch")
    assert rock["key"] == "Left Click"
    assert rock["section"] == "Normal Abilities"
    assert "damage" in rock["description"].lower()
    assert rock["stats"].get("Damage") == "150"
    assert rock["icon"] == "Rock_Punch_Icon.png"


def test_parse_abilities_missing_template_returns_empty():
    with patch("wiki_sync.ability_scraper.fetch_abilities_wikitext", return_value=None):
        abilities = fetch_hero_abilities("Nonexistent Hero")
    assert abilities == []


def test_extract_subtemplates_multi_form():
    pairs = _extract_subtemplates(_MULTI_FORM_WIKITEXT)
    assert len(pairs) == 2
    forms = [label for label, _ in pairs]
    assert "Human" in forms
    assert "Hulk" in forms


def test_fetch_hero_abilities_multi_form():
    def _mock_fetch_template(path: str) -> str | None:
        if path == "Abilities/Bruce Banner":
            return _MULTI_FORM_WIKITEXT
        if "Human" in path:
            return _HUMAN_FORM_WIKITEXT
        if "Hulk" in path:
            return _HULK_FORM_WIKITEXT
        return None

    with patch("wiki_sync.ability_scraper._fetch_template", side_effect=_mock_fetch_template):
        abilities = fetch_hero_abilities("Bruce Banner")

    assert len(abilities) == 2
    forms = {a["form"] for a in abilities}
    assert "Human" in forms
    assert "Hulk" in forms
    names = [a["name"] for a in abilities]
    assert "Gamma Grenade" in names
    assert "Hulk Smash" in names

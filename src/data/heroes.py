import json
import os
import sys


def _json_path() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'heroes.json')
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'heroes.json')
    )


_DEFAULT_ROSTER = [
    "Adam Warlock",
    "Angela",
    "Black Cat",
    "Black Panther",
    "Black Widow",
    "Blade",
    "Bruce Banner",
    "Captain America",
    "Cloak & Dagger",
    "Daredevil",
    "Deadpool",
    "Devil Dinosaur",
    "Doctor Strange",
    "Elsa Bloodstone",
    "Emma Frost",
    "Gambit",
    "Groot",
    "Hawkeye",
    "Hela",
    "Human Torch",
    "Invisible Woman",
    "Iron Fist",
    "Iron Man",
    "Jeff the Land Shark",
    "Loki",
    "Luna Snow",
    "Magik",
    "Magneto",
    "Mantis",
    "Mister Fantastic",
    "Moon Knight",
    "Namor",
    "Peni Parker",
    "Phoenix",
    "Psylocke",
    "Rocket Raccoon",
    "Rogue",
    "Scarlet Witch",
    "Spider-Man",
    "Squirrel Girl",
    "Star-Lord",
    "Storm",
    "The Punisher",
    "The Thing",
    "Thor",
    "Ultron",
    "Venom",
    "White Fox",
    "Winter Soldier",
    "Wolverine",
]

_DEFAULT_ROLES: dict[str, str] = {
    "Adam Warlock": "Strategist",
    "Angela": "Vanguard",
    "Black Cat": "Duelist",
    "Black Panther": "Duelist",
    "Black Widow": "Duelist",
    "Blade": "Duelist",
    "Bruce Banner": "Vanguard",
    "Captain America": "Vanguard",
    "Cloak & Dagger": "Strategist",
    "Daredevil": "Duelist",
    "Deadpool": "Multi-Role",
    "Devil Dinosaur": "Vanguard",
    "Doctor Strange": "Vanguard",
    "Elsa Bloodstone": "Duelist",
    "Emma Frost": "Vanguard",
    "Gambit": "Strategist",
    "Groot": "Vanguard",
    "Hawkeye": "Duelist",
    "Hela": "Duelist",
    "Human Torch": "Duelist",
    "Invisible Woman": "Strategist",
    "Iron Fist": "Duelist",
    "Iron Man": "Duelist",
    "Jeff the Land Shark": "Strategist",
    "Loki": "Strategist",
    "Luna Snow": "Strategist",
    "Magik": "Duelist",
    "Magneto": "Vanguard",
    "Mantis": "Strategist",
    "Mister Fantastic": "Duelist",
    "Moon Knight": "Duelist",
    "Namor": "Duelist",
    "Peni Parker": "Vanguard",
    "Phoenix": "Duelist",
    "Psylocke": "Duelist",
    "Rocket Raccoon": "Strategist",
    "Rogue": "Vanguard",
    "Scarlet Witch": "Duelist",
    "Spider-Man": "Duelist",
    "Squirrel Girl": "Duelist",
    "Star-Lord": "Duelist",
    "Storm": "Duelist",
    "The Punisher": "Duelist",
    "The Thing": "Vanguard",
    "Thor": "Vanguard",
    "Ultron": "Strategist",
    "Venom": "Vanguard",
    "White Fox": "Strategist",
    "Winter Soldier": "Duelist",
    "Wolverine": "Duelist",
}


def _load() -> tuple[list, dict]:
    path = _json_path()
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            return data['roster'], data['roles']
        except Exception:
            pass
    return list(_DEFAULT_ROSTER), dict(_DEFAULT_ROLES)


def _reload():
    """Re-read heroes.json and update the module-level lists in-place."""
    roster, roles = _load()
    HERO_ROSTER.clear()
    HERO_ROSTER.extend(roster)
    HERO_ROLES.clear()
    HERO_ROLES.update(roles)


HERO_ROSTER, HERO_ROLES = _load()

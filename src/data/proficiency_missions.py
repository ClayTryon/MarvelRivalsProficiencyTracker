# Proficiency mission data scraped from:
#   New system (Season 2+):  https://marvelrivals.fandom.com/wiki/Proficiency
#   Old system (Season 0-1.5): https://marvelrivals.fandom.com/wiki/Proficiency/Old_Proficiency
#
# KEY DIFFERENCES BETWEEN SYSTEMS
# ─────────────────────────────────────────────────────────────────────────────
# Old (seasons 0–1.5 / rivalsmeta seasons 1–3):
#   • 4 challenges per rank
#   • Ch1: 60 min playtime (60 pts)
#   • Ch2: stat threshold — fixed per hero, same for all ranks (50 pts)
#   • Ch3: KOs / Final Hits — fixed per hero (50 pts)
#   • Ch4: hero-specific ABILITY usage — unique per hero (50 pts)
#   • Total 210 pts per full completion; need 500 pts to advance from Agent
#
# New (Season 2+ / rivalsmeta seasons 4+, patch 20250425):
#   • 3 challenges per rank
#   • Ch1: 15 min playtime (20 pts permanent / 45 pts daily)
#   • Ch2: stat threshold — SCALES with rank (7/13/20/26/80 pts)
#   • Ch3: KOs / Final Hits — SCALES with rank (7/13/20/26/80 pts)
#   • Ch4: removed
#   • Thresholds increase at each rank up to Lord, then stay flat
#
# Column mapping to match_history for checking per-match completion:
#   damage        → match_history.damage
#   block         → match_history.damage_taken  (rivalsmeta field)
#   healing       → match_history.healing
#   damage_healing→ match_history.damage + match_history.healing  (Deadpool)
#   final_hits    → match_history.kills   (final blow ≈ kill in KDA)
#   kos           → match_history.kills
#   kos_assists   → match_history.kills + match_history.assists
#
# Ch4 (ability) cannot be derived from match_history data — rivalsmeta does
# not expose per-ability usage counts.
# ─────────────────────────────────────────────────────────────────────────────

# rivalsmeta season numbers that use the OLD system (in-game seasons 0, 1, 1.5)
OLD_SYSTEM_SEASONS = {1, 2, 3}

# ── NEW SYSTEM (Season 2+ / rivalsmeta seasons 4+) ───────────────────────────
# Structure:
#   ch2_type: "damage" | "block" | "healing" | "damage_healing"
#   ch2:      {agent, knight, captain, centurion, lord}  per-match threshold
#   ch3_type: "final_hits" | "kos" | "kos_assists"
#   ch3:      {agent, knight, captain, centurion, lord}  per-match threshold
# Centurion and Lord share the same threshold per the wiki.

PROFICIENCY_MISSIONS: dict[str, dict] = {
    "Adam Warlock": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 13,    "knight": 26,    "captain": 38,    "centurion": 51,    "lord": 51},
    },
    "Angela": {
        "ch2_type": "block",
        "ch2": {"agent": 7500,  "knight": 15000, "captain": 22000, "centurion": 30000, "lord": 30000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Black Cat": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Black Panther": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Black Widow": {
        "ch2_type": "damage",
        "ch2": {"agent": 3100,  "knight": 6200,  "captain": 9200,  "centurion": 12000, "lord": 12000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Blade": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Hulk": {
        "ch2_type": "block",
        "ch2": {"agent": 10000, "knight": 21000, "captain": 31000, "centurion": 42000, "lord": 42000},
        "ch3_type": "kos",
        "ch3": {"agent": 5,     "knight": 11,    "captain": 16,    "centurion": 22,    "lord": 22},
    },
    "Captain America": {
        "ch2_type": "block",
        "ch2": {"agent": 9000,  "knight": 18000, "captain": 27000, "centurion": 36000, "lord": 36000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Cloak & Dagger": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Daredevil": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Deadpool": {
        "ch2_type": "damage_healing",
        "ch2": {"agent": 5700,  "knight": 11000, "captain": 17000, "centurion": 23000, "lord": 23000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Devil Dinosaur": {
        "ch2_type": "block",
        "ch2": {"agent": 14000, "knight": 27000, "captain": 41000, "centurion": 55000, "lord": 55000},
        "ch3_type": "kos",
        "ch3": {"agent": 7,     "knight": 15,    "captain": 22,    "centurion": 29,    "lord": 29},
    },
    "Doctor Strange": {
        "ch2_type": "block",
        "ch2": {"agent": 10000, "knight": 21000, "captain": 31000, "centurion": 42000, "lord": 42000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Elsa Bloodstone": {
        "ch2_type": "damage",
        "ch2": {"agent": 5700,  "knight": 11000, "captain": 17000, "centurion": 23000, "lord": 23000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 6,     "knight": 11,    "captain": 17,    "centurion": 23,    "lord": 23},
    },
    "Emma Frost": {
        "ch2_type": "block",
        "ch2": {"agent": 10000, "knight": 21000, "captain": 31000, "centurion": 42000, "lord": 42000},
        "ch3_type": "kos",
        "ch3": {"agent": 7,     "knight": 15,    "captain": 22,    "centurion": 29,    "lord": 29},
    },
    "Gambit": {
        "ch2_type": "healing",
        "ch2": {"agent": 4500,  "knight": 9100,  "captain": 14000, "centurion": 18000, "lord": 18000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Groot": {
        "ch2_type": "block",
        "ch2": {"agent": 14000, "knight": 27000, "captain": 41000, "centurion": 55000, "lord": 55000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Hawkeye": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 6,     "knight": 11,    "captain": 17,    "centurion": 23,    "lord": 23},
    },
    "Hela": {
        "ch2_type": "damage",
        "ch2": {"agent": 5700,  "knight": 11000, "captain": 17000, "centurion": 23000, "lord": 23000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 7,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Human Torch": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Invisible Woman": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Iron Fist": {
        "ch2_type": "damage",
        "ch2": {"agent": 3100,  "knight": 6200,  "captain": 9200,  "centurion": 12000, "lord": 12000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Iron Man": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Jeff the Land Shark": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 13,    "knight": 26,    "captain": 38,    "centurion": 51,    "lord": 51},
    },
    "Loki": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Luna Snow": {
        "ch2_type": "healing",
        "ch2": {"agent": 6200,  "knight": 12000, "captain": 18000, "centurion": 25000, "lord": 25000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Magik": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Magneto": {
        "ch2_type": "block",
        "ch2": {"agent": 9000,  "knight": 18000, "captain": 27000, "centurion": 36000, "lord": 36000},
        "ch3_type": "kos",
        "ch3": {"agent": 7,     "knight": 15,    "captain": 22,    "centurion": 29,    "lord": 29},
    },
    "Mantis": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 17,    "knight": 35,    "captain": 52,    "centurion": 70,    "lord": 70},
    },
    "Mister Fantastic": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Moon Knight": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Namor": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Peni Parker": {
        "ch2_type": "block",
        "ch2": {"agent": 7500,  "knight": 15000, "captain": 22000, "centurion": 30000, "lord": 30000},
        "ch3_type": "kos",
        "ch3": {"agent": 7,     "knight": 15,    "captain": 22,    "centurion": 29,    "lord": 29},
    },
    "Phoenix": {
        "ch2_type": "damage",
        "ch2": {"agent": 5700,  "knight": 11000, "captain": 17000, "centurion": 23000, "lord": 23000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 7,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Psylocke": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Rocket Raccoon": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Rogue": {
        "ch2_type": "block",
        "ch2": {"agent": 9000,  "knight": 18000, "captain": 27000, "centurion": 36000, "lord": 36000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Scarlet Witch": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Spider-Man": {
        "ch2_type": "damage",
        "ch2": {"agent": 3100,  "knight": 6200,  "captain": 9200,  "centurion": 12000, "lord": 12000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Squirrel Girl": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Star-Lord": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "Storm": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "The Punisher": {
        "ch2_type": "damage",
        "ch2": {"agent": 5100,  "knight": 10000, "captain": 15000, "centurion": 20000, "lord": 20000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
    "The Thing": {
        "ch2_type": "block",
        "ch2": {"agent": 10000, "knight": 21000, "captain": 31000, "centurion": 42000, "lord": 42000},
        "ch3_type": "kos",
        "ch3": {"agent": 7,     "knight": 15,    "captain": 22,    "centurion": 29,    "lord": 29},
    },
    "Thor": {
        "ch2_type": "block",
        "ch2": {"agent": 9000,  "knight": 18000, "captain": 27000, "centurion": 36000, "lord": 36000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "Ultron": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 17,    "knight": 35,    "captain": 52,    "centurion": 70,    "lord": 70},
    },
    "Venom": {
        "ch2_type": "block",
        "ch2": {"agent": 10000, "knight": 21000, "captain": 31000, "centurion": 42000, "lord": 42000},
        "ch3_type": "kos",
        "ch3": {"agent": 6,     "knight": 13,    "captain": 19,    "centurion": 25,    "lord": 25},
    },
    "White Fox": {
        "ch2_type": "healing",
        "ch2": {"agent": 5400,  "knight": 11000, "captain": 16000, "centurion": 21000, "lord": 21000},
        "ch3_type": "kos_assists",
        "ch3": {"agent": 15,    "knight": 30,    "captain": 45,    "centurion": 60,    "lord": 60},
    },
    "Winter Soldier": {
        "ch2_type": "damage",
        "ch2": {"agent": 3700,  "knight": 7500,  "captain": 11000, "centurion": 15000, "lord": 15000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 4,     "knight": 8,     "captain": 12,    "centurion": 17,    "lord": 17},
    },
    "Wolverine": {
        "ch2_type": "damage",
        "ch2": {"agent": 4400,  "knight": 8800,  "captain": 13000, "centurion": 18000, "lord": 18000},
        "ch3_type": "final_hits",
        "ch3": {"agent": 5,     "knight": 10,    "captain": 15,    "centurion": 20,    "lord": 20},
    },
}

# ── OLD SYSTEM (Seasons 0–1.5 / rivalsmeta seasons 1–3) ──────────────────────
# Structure:
#   ch2_type / ch2_threshold: stat challenge (single fixed threshold, all ranks)
#   ch3_type / ch3_threshold: KOs/Final Hits (single fixed threshold, all ranks)
#   ch4_desc:  hero-specific ability challenge description (not trackable from API)
# Ch1 was always "Hero usage time reaches 60 minutes" (60 pts).

OLD_PROFICIENCY_MISSIONS: dict[str, dict] = {
    "Adam Warlock": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 20,
        "ch4_desc": "Revive 5 allies with Karmic Revival",
    },
    "Angela": {
        "ch2_type": "block",  "ch2_threshold": 15000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Accumulate 3,000 Attack Charge",
    },
    "Black Panther": {
        "ch2_type": "damage",      "ch2_threshold": 7500,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Use Spirit Rend 30 times",
    },
    "Black Widow": {
        "ch2_type": "damage",      "ch2_threshold": 6000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Achieve 5 Critical KOs",
    },
    "Blade": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Lifesteal 2,500 Health with Bloodline Awakening",
    },
    "Hulk": {
        "ch2_type": "block",  "ch2_threshold": 21000,
        "ch3_type": "kos",    "ch3_threshold": 10,
        "ch4_desc": "Add Indestructible Guard to 20 allies",
    },
    "Captain America": {
        "ch2_type": "block",  "ch2_threshold": 20000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Grant 3,500 bonus Health with Freedom Charge",
    },
    "Cloak & Dagger": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 15,
        "ch4_desc": "Use Terror Cape to score hits on 10 heroes",
    },
    "Daredevil": {
        "ch2_type": "damage",      "ch2_threshold": 7500,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Accumulate 140 Fury",
    },
    "Doctor Strange": {
        "ch2_type": "block",  "ch2_threshold": 21000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Release 6 souls with Eye of Agamotto",
    },
    "Emma Frost": {
        "ch2_type": "block",  "ch2_threshold": 21000,
        "ch3_type": "kos",    "ch3_threshold": 15,
        "ch4_desc": "Seize control of 6 sentiences with Psychic Spear",
    },
    "Gambit": {
        "ch2_type": "healing",     "ch2_threshold": 9000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Use 50 Sleight of Hand Stacks",
    },
    "Groot": {
        "ch2_type": "block",  "ch2_threshold": 27000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Build 50 Wooden Walls",
    },
    "Hawkeye": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 12,
        "ch4_desc": "Score 40 hits with Hypersonic Arrow",
    },
    "Hela": {
        "ch2_type": "damage",      "ch2_threshold": 11000,
        "ch3_type": "final_hits",  "ch3_threshold": 12,
        "ch4_desc": "Stun 6 enemies with Soul Drainer",
    },
    "Human Torch": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Create 200 flame fields with Blazing Blast",
    },
    "Invisible Woman": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Block 5,000 damage with Guardian Shield",
    },
    "Iron Fist": {
        "ch2_type": "damage",      "ch2_threshold": 6000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Grant 1,500 bonus Health with Dragon's Defense",
    },
    "Iron Man": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Directly hit enemies 50 times with Repulsor Blast",
    },
    "Jeff the Land Shark": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 20,
        "ch4_desc": "Swallow 4 heroes with It's Jeff!",
    },
    "Loki": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Conjure a total of 40 Illusions",
    },
    "Luna Snow": {
        "ch2_type": "healing",     "ch2_threshold": 12000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Freeze 4 enemies with Absolute Zero",
    },
    "Magik": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Gain 2,500 extra Health with Limbo's Might",
    },
    "Magneto": {
        "ch2_type": "block",  "ch2_threshold": 20000,
        "ch3_type": "kos",    "ch3_threshold": 15,
        "ch4_desc": "Absorb 2,000 damage with Meteor M",
    },
    "Mantis": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Sedate 5 enemies with Spore Slumber",
    },
    "Mister Fantastic": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Enter Inflated state 15 times",
    },
    "Moon Knight": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Inflict 400 bounces on enemies using Ankhs",
    },
    "Namor": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Summon 50 Monstro Spawns",
    },
    "Peni Parker": {
        "ch2_type": "block",  "ch2_threshold": 15000,
        "ch3_type": "kos",    "ch3_threshold": 15,
        "ch4_desc": "Deal 2,500 Damage with Arachno-Mine",
    },
    "Psylocke": {
        "ch2_type": "damage",      "ch2_threshold": 7500,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Use Psychic Stealth to accumulate 40 seconds of invisibility",
    },
    "Rocket Raccoon": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Revive 6 allies with B.R.B.",
    },
    "Rogue": {
        "ch2_type": "block",  "ch2_threshold": 20000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Use Ability Absorption on 10 heroes",
    },
    "Scarlet Witch": {
        "ch2_type": "damage",      "ch2_threshold": 7500,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Stun 6 enemies with Dark Seal",
    },
    "Spider-Man": {
        "ch2_type": "damage",      "ch2_threshold": 6000,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Trigger Spider-Tracers 40 times",
    },
    "Squirrel Girl": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Immobilize 10 enemies with Squirrel Blockade",
    },
    "Star-Lord": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Switch 1,000 magazines with Stellar Shift",
    },
    "Storm": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Use Goddess Boost on 75 heroes",
    },
    "The Punisher": {
        "ch2_type": "damage",      "ch2_threshold": 10000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Envelop 20 enemies with Scourge Grenade",
    },
    "The Thing": {
        "ch2_type": "block",  "ch2_threshold": 21000,
        "ch3_type": "kos",    "ch3_threshold": 15,
        "ch4_desc": "Hit 30 enemies with Yancy Street Charge",
    },
    "Thor": {
        "ch2_type": "block",  "ch2_threshold": 20000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Accumulate 120 Thorforce",
    },
    "Ultron": {
        "ch2_type": "healing",     "ch2_threshold": 10000,
        "ch3_type": "kos_assists", "ch3_threshold": 25,
        "ch4_desc": "Use Imperative: Firewall to cumulatively add 4,000 extra Health",
    },
    "Venom": {
        "ch2_type": "block",  "ch2_threshold": 20000,
        "ch3_type": "kos",    "ch3_threshold": 12,
        "ch4_desc": "Gain 8,000 bonus Health with Symbiotic Resilience",
    },
    "Winter Soldier": {
        "ch2_type": "damage",      "ch2_threshold": 7500,
        "ch3_type": "final_hits",  "ch3_threshold": 8,
        "ch4_desc": "Grab 15 enemies with Bionic Hook",
    },
    "Wolverine": {
        "ch2_type": "damage",      "ch2_threshold": 8000,
        "ch3_type": "final_hits",  "ch3_threshold": 10,
        "ch4_desc": "Knock down 10 enemies with Feral Leap",
    },
}

# ── Rank ↔ Level mapping ──────────────────────────────────────────────────────
# Aligns exactly with XP band breakpoints in data/xp_table.py:
#   Levels 1–4   = Agent    (125 XP/level,  0–499 cumulative)
#   Levels 5–9   = Knight   (240 XP/level,  500–1699 cumulative)
#   Levels 10–14 = Captain  (400 XP/level,  1700–3699 cumulative)
#   Levels 15–19 = Centurion(480 XP/level,  3700–6099 cumulative)
#   Levels 20+   = Lord     (1600 XP/level, 6100+ cumulative)

_RANK_THRESHOLDS = [
    (20, "lord"),
    (15, "centurion"),
    (10, "captain"),
    (5,  "knight"),
    (1,  "agent"),
]

def rank_for_level(level: int) -> str:
    for threshold, name in _RANK_THRESHOLDS:
        if level >= threshold:
            return name
    return "agent"

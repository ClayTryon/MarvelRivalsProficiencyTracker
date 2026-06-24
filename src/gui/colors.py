# ── Core application backgrounds ──────────────────────────────────────────────
BG_APP          = "#0c0c14"   # main window / dialog / scrollbar track
BG_DEEP         = "#080810"   # header bars, darkest panels
BG_SINK         = "#0a0a12"   # text-edit widget, chart axis area
BG_CONTROL      = "#16162a"   # buttons, combos, inputs, menus (default state)
BG_HOVER        = "#1e1e34"   # control hover state / spin-box arrows
BG_PRESSED      = "#0c0c1c"   # button pressed state
BG_SELECT       = "#222240"   # menu / combo selection highlight

# ── Card and panel surfaces ───────────────────────────────────────────────────
BG_CARD         = "#0d1628"   # hero detail card surface
BG_CARD_ALT     = "#080f1e"   # image placeholders, darker card areas
BG_PANEL        = "#141420"   # side info panel
BG_ICON         = "#141414"   # icon placeholder (hero card)
BG_INPUT        = "#12121e"   # inline input fields
BG_HOVER_INPUT  = "#1e1e30"   # inline input hover
DARK            = "#1a1a1a"   # hero card background / text on gold-accent buttons

# ── Borders and separators ────────────────────────────────────────────────────
BORDER          = "#26263c"   # standard control border
BORDER_MID      = "#1a1a2c"   # mid separator, progress bg, spin disabled bg
BORDER_SINK     = "#1c1c2c"   # text-edit border
BORDER_DEEP     = "#141424"   # section-header bottom rule
BORDER_CARD     = "#1a2a44"   # hero / team-up card border
BORDER_INPUT    = "#2a2a4a"   # inline input / dialog border
BORDER_NAV      = "#2a2a40"   # nav-bar separator
SCROLL_HANDLE   = "#26263a"   # scrollbar handle (resting)
PROGRESS_BG     = "#2a2a2a"   # hero-card progress-bar track / card resting border
BTN_DISABLED_BG = "#2a2a3a"   # disabled primary button background

# ── Text colours ──────────────────────────────────────────────────────────────
TEXT            = "#dcdce8"   # primary label text
TEXT_UI         = "#a8a8c0"   # control text (buttons, combos, menus)
TEXT_BRIGHT     = "#e0e0f0"   # control hover / high-contrast text
TEXT_DIALOG     = "#e0e0e0"   # dialog base text / progress-bar label
TEXT_NEAR_WHITE = "#e8e8e8"   # ability card headers / hero-card names
TEXT_BODY       = "#c8c8e0"   # chat / body panel text
TEXT_MUTED      = "#7878a0"   # log output / chart secondary axis
TEXT_NAV_HOVER  = "#9090b8"   # nav-tab hover colour
TEXT_SUB        = "#606078"   # form-row labels / chart sub-text
TEXT_DIM        = "#484860"   # dim / placeholder labels
TEXT_FAINT      = "#363650"   # disabled / very-faint text
TEXT_VER        = "#303048"   # version number
TEXT_BRONZE     = "#c8a84b"   # ShowAll dialog section-header accent
TEXT_GRAY       = "#888888"   # neutral-gray labels
TEXT_LIGHT_GRAY = "#aaaaaa"   # light-gray status messages
TEXT_HOVER_GRAY = "#bbbbbb"   # hover text on dim / inactive buttons
TEXT_LOG        = "#cccccc"   # sync log output
GRAY_55         = "#555555"   # very dim: key annotations, empty states, disabled
GRAY_66         = "#666666"   # inactive button / tab text, dim field labels

# ── Accent / highlight colours ────────────────────────────────────────────────
GOLD            = "#f4d641"   # primary gold accent (XP bars, active nav, focus)
GOLD_HOVER      = "#ffe066"   # gold hover state
GOLD_PRESS      = "#c8b030"   # gold pressed state
GOLD_MAX        = "#FFD700"   # max-level (Champion) badge
GOLD_BG         = "#1a1a00"   # dark background for gold-accent buttons
BLUE_ACCENT     = "#a0c8ff"   # team-up labels / XP chart line

# ── Rarity tier colours ───────────────────────────────────────────────────────
RARITY_LEGENDARY = GOLD        # alias — same gold as the primary accent
RARITY_EPIC      = "#b060f0"
RARITY_RARE      = "#4090e0"
RARITY_COMMON    = TEXT_GRAY   # alias — same neutral gray
RARITY_UNKNOWN   = "#444444"

# ── Hero role colours ─────────────────────────────────────────────────────────
ROLE_VANGUARD   = "#4a90d9"
ROLE_DUELIST    = "#d94a4a"
ROLE_STRATEGIST = "#4ad98a"
ROLE_MULTI_ROLE = "#d9a44a"

# ── Status / feedback colours ─────────────────────────────────────────────────
ERR             = "#c84040"   # error red
ERR_BG          = "#1a0000"   # error dark background
ERR_LIGHT       = "#ff8888"   # cancel-button / light error text
WARN            = "#b0903a"   # warning amber
WARN_BG         = "#1a1400"   # warning background
WARN_BORDER     = "#3a2e00"   # warning border
UPDATE_BG       = "#3a3000"   # update-available banner background

# ── Misc widget colours ───────────────────────────────────────────────────────
COMBO_ARROW      = "#686880"   # combo-box down-arrow indicator
TEAMUP_INACTIVE  = "#1e2a42"   # portrait border when not selected
TEAMUP_ABILITY   = "#4a5a78"   # team-up ability-name label
TEAMUP_DESC      = "#8a9ab8"   # team-up description text
TEAMUP_STATS     = "#555566"   # team-up stats value text  (CSS #556 expanded)
TEAMUP_STATS_KEY = "#666677"   # team-up stats key text    (CSS #667 expanded)

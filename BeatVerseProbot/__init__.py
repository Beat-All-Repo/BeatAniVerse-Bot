# ==============================================================================
# PLACE AT: /app/BeatVerseProbot/__init__.py
# ACTION: Replace existing file
# ==============================================================================
"""
BeatVerseProbot — compatibility stub package.
Fully patches sys.modules so all BeatVerseProbot.* imports resolve.
Critically: BeatVerseProbot.modules.connection → modules.connection
"""
import os, sys, types, logging
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "")
STATS = {}; USER_INFO = {}; DATA_IMPORT = {}; DATA_EXPORT = {}
CHAT_SETTINGS = {}; HELPABLE = {}; IMPORTED = {}
MIGRATEABLE = []; USER_SETTINGS = {}; EXPORTED = {}

_this = sys.modules[__name__]

def _make_stub(name: str, **attrs):
    if name in sys.modules:
        return sys.modules[name]
    m = types.ModuleType(name)
    m.__package__ = name.rsplit(".", 1)[0] if "." in name else name
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

# ── BeatVerseProbot.modules → forward all attrs to real modules package ───────
class _ModulesProxy(types.ModuleType):
    """
    Proxy for BeatVerseProbot.modules that forwards attribute access to the
    real modules.* package. So `from BeatVerseProbot.modules import connection`
    returns the real modules.connection module.
    """
    def __init__(self):
        super().__init__("BeatVerseProbot.modules")
        self.__package__ = "BeatVerseProbot"
        self.__path__ = []  # marks it as a package

    def __getattr__(self, name):
        # Try to import modules.<name> directly
        try:
            import importlib
            real = importlib.import_module(f"modules.{name}")
            setattr(self, name, real)   # cache for next access
            return real
        except ImportError:
            pass
        # Sub-path stub: BeatVerseProbot.modules.something
        sub_name = f"BeatVerseProbot.modules.{name}"
        if sub_name in sys.modules:
            return sys.modules[sub_name]
        stub = _make_stub(sub_name)
        setattr(self, name, stub)
        return stub

_modules_proxy = _ModulesProxy()
sys.modules["BeatVerseProbot.modules"] = _modules_proxy
setattr(_this, "modules", _modules_proxy)

# ── Register all other BeatVerseProbot.* stubs ────────────────────────────────
for _path in [
    "BeatVerseProbot.utils",
    "BeatVerseProbot.utils.mongo",
    "BeatVerseProbot.utils.fonts",
    "BeatVerseProbot.events",
    "BeatVerseProbot.__main__",
]:
    _make_stub(_path)

# Ensure self is in sys.modules
sys.modules["BeatVerseProbot"] = _this

# ── events.register decorator ─────────────────────────────────────────────────
def _register(*args, **kwargs):
    def decorator(func): return func
    if args and callable(args[0]): return args[0]
    return decorator

_events_mod = sys.modules["BeatVerseProbot.events"]
_events_mod.register = _register
setattr(_this, "events", _events_mod)

# ── utils.mongo stubs ─────────────────────────────────────────────────────────
_mongo_mod = sys.modules["BeatVerseProbot.utils.mongo"]

async def _get_couple(chat_id, date):
    try:
        from database_dual import _MG
        if _MG and _MG.db:
            return _MG.db.couples.find_one({"chat_id": chat_id, "date": date})
    except Exception: pass
    return None

async def _save_couple(chat_id, date, couple):
    try:
        from database_dual import _MG
        if _MG and _MG.db:
            _MG.db.couples.update_one(
                {"chat_id": chat_id, "date": date},
                {"$set": {**couple, "chat_id": chat_id, "date": date}},
                upsert=True)
            return True
    except Exception: pass
    return False

_mongo_mod.get_couple = _get_couple
_mongo_mod.save_couple = _save_couple

# ── utils.fonts stub ──────────────────────────────────────────────────────────
_fonts_mod = sys.modules["BeatVerseProbot.utils.fonts"]
class _Fonts:
    @staticmethod
    def convert(t, s=""): return t
    def __call__(self, t, *a, **k): return t
_fonts_mod.Fonts = _Fonts

# ── __main__ stubs ─────────────────────────────────────────────────────────────
_main_mod = sys.modules["BeatVerseProbot.__main__"]
for _attr in ("TOKEN","STATS","USER_INFO","DATA_IMPORT","DATA_EXPORT",
              "CHAT_SETTINGS","HELPABLE","IMPORTED","MIGRATEABLE","USER_SETTINGS","EXPORTED"):
    setattr(_main_mod, _attr, globals().get(_attr, {}))

# ── fun_strings forward ────────────────────────────────────────────────────────
_fun_path = "BeatVerseProbot.modules.fun_strings"
if _fun_path not in sys.modules:
    _fun_mod = _make_stub(_fun_path)
    try:
        from modules.fun_strings import RUN_STRINGS, SLAP_TEMPLATES, PAT_TEMPLATES, ITEMS
        _fun_mod.RUN_STRINGS = RUN_STRINGS
        _fun_mod.SLAP_TEMPLATES = SLAP_TEMPLATES
        _fun_mod.PAT_TEMPLATES = PAT_TEMPLATES
        _fun_mod.ITEMS = ITEMS
    except Exception:
        _fun_mod.RUN_STRINGS = ("Running!",)
        _fun_mod.SLAP_TEMPLATES = ("{user1} slapped {user2}.",)
        _fun_mod.PAT_TEMPLATES = ("{user1} patted {user2}.",)
        _fun_mod.ITEMS = ("bat",)

logger.debug("[BeatVerseProbot] stub package fully initialised with module proxy")

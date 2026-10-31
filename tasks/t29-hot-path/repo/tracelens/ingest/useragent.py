"""A rough user-agent classifier. Good enough for traffic splits, not for fingerprinting."""
import re

_BROWSERS = [
    ("edge", re.compile(r"Edg/")),
    ("chrome", re.compile(r"Chrome/")),
    ("firefox", re.compile(r"Firefox/")),
    ("safari", re.compile(r"Safari/")),
]
_SYSTEMS = [
    ("android", re.compile(r"Android")),
    ("ios", re.compile(r"iPhone|iPad")),
    ("windows", re.compile(r"Windows")),
    ("mac", re.compile(r"Macintosh")),
    ("linux", re.compile(r"Linux")),
]
_BOT = re.compile(r"bot|crawler|spider|slurp|headless", re.I)


def classify(agent):
    """(browser, system, is_bot) for a user-agent string."""
    agent = agent or ""
    if _BOT.search(agent):
        return "bot", "other", True
    browser = next((name for name, rx in _BROWSERS if rx.search(agent)), "other")
    system = next((name for name, rx in _SYSTEMS if rx.search(agent)), "other")
    return browser, system, False


def device(agent):
    browser, system, is_bot = classify(agent)
    if is_bot:
        return "bot"
    return "mobile" if system in ("android", "ios") else "desktop"

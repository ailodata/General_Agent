"""Synthetic website data for a fictional Nordic restaurant chain ("Bistro Lind").

One table, one row per event (pageview or conversion), so a marketing analytics agent can answer
questions about channels, content, markets, journeys, time to convert and conversion rates
(per visitor and per session).

Everything here is invented. No real company or customer data is used.

Run:  python data_generator/generate_data.py   -> writes data/website_events.csv
"""
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
START = date(2026, 4, 1)
END = date(2026, 10, 18)
BASE_SESSIONS_PER_DAY = 200
OUT = Path(__file__).resolve().parent.parent / "data"

rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------------------
# Site structure
# --------------------------------------------------------------------------------------
MARKETS = {
    "en": {"prefix": "", "language": "en", "weight": 0.38, "label": "English"},
    "da": {"prefix": "/da-dk", "language": "da-dk", "weight": 0.29, "label": "Danish"},
    "sv": {"prefix": "/sv-se", "language": "sv-se", "weight": 0.21, "label": "Swedish"},
    "no": {"prefix": "/no-no", "language": "no-no", "weight": 0.12, "label": "Norwegian"},
}
CITIES = {  # city -> market that "owns" it
    "Copenhagen": "da", "Aarhus": "da", "Stockholm": "sv", "Gothenburg": "sv", "Oslo": "no", "Bergen": "no",
}
BOOKING_DOMAIN = "book.bistrolind.example"
SITE_DOMAIN = "bistrolind.example"

# topic -> (content_type, funnel_stage)
TOPICS = {
    "homepage": ("STANDARD_PAGE", "top"),
    "about": ("STANDARD_PAGE", "top"),
    "menu_dinner": ("STANDARD_PAGE", "mid"),
    "menu_lunch": ("STANDARD_PAGE", "mid"),
    "menu_drinks": ("STANDARD_PAGE", "mid"),
    "menu_vegan": ("STANDARD_PAGE", "mid"),
    "locations": ("STANDARD_PAGE", "mid"),
    "booking": ("STANDARD_PAGE", "bottom"),
    "booking_widget": (None, "bottom"),
    "catering_events": ("STANDARD_PAGE", "mid"),
    "gift_cards": ("STANDARD_PAGE", "mid"),
    "loyalty": ("STANDARD_PAGE", "mid"),
    "campaign_landing": ("LANDING_PAGE", "top"),
    "blog_recipes": ("BLOG_POST", "top"),
    "blog_chef_stories": ("BLOG_POST", "top"),
    "blog_sustainability": ("BLOG_POST", "top"),
    "blog_company_news": ("BLOG_POST", "top"),
    "blog_listing": ("LISTING_PAGE", "top"),
    "careers": ("STANDARD_PAGE", "other"),
    "contact": ("STANDARD_PAGE", "bottom"),
    "legal": ("STANDARD_PAGE", "other"),
}

T = lambda en, da=None, sv=None, no=None: {"en": en, "da": da or en, "sv": sv or en, "no": no or en}

# (topic, path, titles, markets or None for all)
PAGES = [
    ("homepage", "/", T("Bistro Lind – Nordic food, made fresh", "Bistro Lind – Nordisk mad, lavet fra bunden",
                        "Bistro Lind – Nordisk mat, lagad från grunden", "Bistro Lind – Nordisk mat, laget fra bunnen"), None),
    ("about", "/about", T("Our story", "Vores historie", "Vår historia", "Vår historie"), None),
    ("menu_dinner", "/menu/dinner", T("Dinner menu", "Aftensmenu", "Middagsmeny", "Middagsmeny"), None),
    ("menu_lunch", "/menu/lunch", T("Lunch menu", "Frokostmenu", "Lunchmeny", "Lunsjmeny"), None),
    ("menu_drinks", "/menu/drinks", T("Drinks & wine", "Drinks og vin", "Drinkar och vin", "Drinker og vin"), None),
    ("menu_vegan", "/menu/plant-based", T("Plant-based menu", "Plantebaseret menu", "Växtbaserad meny", "Plantebasert meny"), None),
    ("locations", "/locations", T("Our restaurants", "Vores restauranter", "Våra restauranger", "Våre restauranger"), None),
    ("booking", "/book-a-table", T("Book a table", "Book bord", "Boka bord", "Bestill bord"), None),
    ("catering_events", "/catering", T("Catering & private dining", "Catering og selskaber", "Catering och sällskap", "Catering og selskap"), None),
    ("catering_events", "/events", T("Events & group bookings", "Events og gruppebookinger", "Event och grupper", "Event og grupper"), None),
    ("gift_cards", "/gift-cards", T("Gift cards", "Gavekort", "Presentkort", "Gavekort"), None),
    ("loyalty", "/lind-club", T("Lind Club – our loyalty programme", "Lind Club – vores kundeklub", "Lind Club – vår kundklubb", "Lind Club – vår kundeklubb"), None),
    ("campaign_landing", "/campaigns/summer-terrace", T("Summer terrace 2026", "Sommerterrasse 2026", "Sommarterrass 2026", "Sommerterrasse 2026"), None),
    ("campaign_landing", "/campaigns/christmas-menu", T("Christmas menu 2026", "Julemenu 2026", "Julmeny 2026", "Julemeny 2026"), None),
    ("careers", "/jobs", T("Careers", "Job hos os", "Jobba hos oss", "Jobb hos oss"), None),
    ("contact", "/contact", T("Contact us", "Kontakt os", "Kontakta oss", "Kontakt oss"), None),
    ("legal", "/legal/privacy", T("Privacy policy", "Privatlivspolitik", "Integritetspolicy", "Personvern"), None),
    ("legal", "/legal/terms", T("Terms and conditions", "Handelsbetingelser", "Villkor", "Vilkår"), None),
    ("blog_listing", "/blog", T("Stories from the kitchen"), ["en"]),
]
for city, owner in CITIES.items():
    slug = city.lower()
    PAGES.append(("locations", f"/locations/{slug}", T(f"Bistro Lind {city}"), ["en", owner]))

BLOGS = {
    "blog_recipes": [
        ("perfect-nordic-rye-bread", T("How to make perfect Nordic rye bread", "Sådan laver du perfekt nordisk rugbrød", "Så bakar du perfekt nordiskt rågbröd"), ["en", "da", "sv"]),
        ("pickled-herring-three-ways", T("Pickled herring three ways", "Syltet sild på tre måder", "Inlagd sill på tre sätt"), ["en", "da", "sv"]),
        ("fish-soup-in-30-minutes", T("A weeknight fish soup in 30 minutes", "En hurtig fiskesuppe på 30 minutter", "En snabb fiskesoppa på 30 minuter"), ["en", "da", "sv"]),
        ("smorrebrod-ideas-for-lunch", T("Smørrebrød ideas for lunch"), ["en"]),
        ("brown-butter-root-vegetables", T("Slow-roasted root vegetables with brown butter"), ["en"]),
        ("homemade-skyr-with-berries", T("Homemade skyr with berries"), ["en"]),
        ("the-ultimate-cinnamon-bun", T("The ultimate cinnamon bun"), ["en"]),
        ("gluhwein-and-mulled-wine-at-home", T("Glögg and mulled wine at home"), ["en"]),
    ],
    "blog_chef_stories": [
        ("meet-our-head-chef-copenhagen", T("Meet our head chef in Copenhagen"), ["en"]),
        ("a-day-in-the-kitchen-stockholm", T("A day in the kitchen at Bistro Lind Stockholm"), ["en"]),
        ("why-we-cook-with-fire", T("Why we cook with fire"), ["en"]),
        ("from-farm-to-table", T("From farm to table: our suppliers"), ["en"]),
    ],
    "blog_sustainability": [
        ("our-zero-waste-kitchen", T("Our zero-waste kitchen"), ["en"]),
        ("sourcing-fish-responsibly", T("Sourcing fish responsibly"), ["en"]),
        ("cutting-food-waste-by-40-percent", T("Cutting food waste by 40%"), ["en"]),
    ],
    "blog_company_news": [
        ("we-are-opening-in-bergen", T("We are opening in Bergen"), ["en"]),
        ("new-summer-terrace-in-aarhus", T("New summer terrace in Aarhus"), ["en"]),
        ("lind-club-turns-one", T("Lind Club turns one"), ["en"]),
    ],
}
for topic, posts in BLOGS.items():
    for slug, titles, mk in posts:
        PAGES.append((topic, f"/blog/{slug}", titles, mk))

# Build the catalogue: topic -> market -> list of page dicts
CATALOG = {}
for topic, path, titles, mk in PAGES:
    ctype, funnel = TOPICS[topic]
    for m, info in MARKETS.items():
        if mk is not None and m not in mk:
            continue
        full_path = (info["prefix"] + path) if path != "/" else (info["prefix"] or "/")
        page = {"topic": topic, "path": full_path, "title": titles[m], "content_type": ctype,
                "funnel": funnel, "language": info["language"], "market": m}
        CATALOG.setdefault(topic, {}).setdefault(m, []).append(page)

WIDGET_PATH = "/reservations"
WIDGET_TITLE = "Reservations"


def pick_page(topic, market, loc_hint=None):
    """Pick a concrete page for a topic in a market (falls back to English)."""
    pages = CATALOG[topic].get(market) or CATALOG[topic]["en"]
    if topic == "locations":
        detail = [p for p in pages if p["path"].count("/") >= (3 if market != "en" else 2)]
        general = [p for p in pages if p not in detail]
        if loc_hint:
            hit = [p for p in detail if p["path"].endswith(loc_hint)]
            if hit:
                return hit[0]
        pool = general * 3 + detail
        return rng.choice(pool)
    if topic.startswith("blog_") and topic != "blog_listing":
        w = [2.0 if "rye" in p["path"] or "herring" in p["path"] else 1.0 for p in pages]
        return rng.choices(pages, weights=w)[0]
    return rng.choice(pages)


# --------------------------------------------------------------------------------------
# Behaviour model
# --------------------------------------------------------------------------------------
CHANNELS = ["direct", "organic", "paid", "social", "email", "referrals", "ai-referrals"]

# intent weights by channel (recipes pull a lot of organic and social traffic, but readers rarely convert)
INTENT_BY_CHANNEL = {
    "direct":       {"booking": .30, "browse_menu": .20, "info": .15, "loyalty": .05, "gift": .05, "blog_read": .05, "newsletter": .02, "catering": .05},
    "organic":      {"booking": .20, "browse_menu": .22, "blog_read": .26, "info": .13, "catering": .04, "gift": .03, "loyalty": .03, "newsletter": .04},
    "paid":         {"booking": .36, "browse_menu": .20, "info": .08, "gift": .08, "loyalty": .05, "newsletter": .06, "blog_read": .03, "catering": .02},
    "social":       {"blog_read": .38, "newsletter": .12, "browse_menu": .20, "booking": .08, "loyalty": .06, "info": .07, "gift": .03, "catering": .01},
    "email":        {"loyalty": .18, "gift": .15, "booking": .25, "newsletter": .02, "browse_menu": .20, "info": .06, "blog_read": .05, "catering": .03},
    "referrals":    {"booking": .35, "browse_menu": .30, "info": .15, "blog_read": .05, "catering": .03, "gift": .02, "loyalty": .02, "newsletter": .02},
    "ai-referrals": {"browse_menu": .35, "info": .20, "booking": .25, "blog_read": .05, "gift": .03, "loyalty": .03, "catering": .03, "newsletter": .01},
}

# journey templates per intent: (sequence of topics, weight); last topic of conversion intents is the conversion page
SEQS = {
    "booking": [(["homepage", "menu_dinner", "booking"], .17), (["homepage", "booking"], .10), (["locations", "booking"], .13),
                (["menu_dinner", "booking"], .11), (["homepage", "menu_lunch", "locations", "booking"], .07), (["campaign_landing", "booking"], .13),
                (["locations", "menu_dinner", "booking"], .12), (["homepage", "menu_dinner", "locations", "booking"], .13),
                (["blog_chef_stories", "homepage", "booking"], .04)],
    "gift": [(["homepage", "gift_cards"], .40), (["gift_cards"], .25), (["campaign_landing", "gift_cards"], .12),
             (["homepage", "menu_dinner", "gift_cards"], .13), (["blog_company_news", "gift_cards"], .10)],
    "loyalty": [(["homepage", "loyalty"], .35), (["loyalty"], .20), (["homepage", "menu_dinner", "loyalty"], .15),
                (["campaign_landing", "loyalty"], .10), (["blog_chef_stories", "loyalty"], .10), (["homepage", "menu_lunch", "loyalty"], .10)],
    "catering": [(["homepage", "catering_events"], .25), (["catering_events", "menu_dinner", "contact"], .20),
                 (["homepage", "catering_events", "contact"], .20), (["about", "catering_events", "contact"], .10),
                 (["homepage", "catering_events", "catering_events", "contact"], .15), (["catering_events", "contact"], .10)],
    "newsletter": [(["blog_chef_stories"], .22), (["homepage"], .20), (["blog_sustainability"], .16), (["campaign_landing"], .12),
                   (["blog_chef_stories", "homepage"], .10), (["homepage", "menu_dinner"], .08), (["blog_company_news"], .06), (["blog_recipes"], .06)],
    "browse_menu": [(["menu_dinner"], .25), (["menu_lunch", "menu_drinks"], .15), (["homepage", "menu_dinner", "menu_vegan"], .12),
                    (["homepage", "menu_dinner"], .20), (["homepage", "menu_lunch"], .15), (["menu_vegan"], .06), (["homepage", "menu_drinks"], .07)],
    "blog_read": [(["blog_recipes"], .55), (["blog_recipes", "blog_recipes"], .15), (["blog_chef_stories"], .07), (["blog_sustainability"], .05),
                  (["blog_company_news"], .05), (["blog_listing", "blog_recipes"], .08), (["blog_recipes", "homepage"], .05)],
    "info": [(["locations"], .30), (["contact"], .15), (["about"], .15), (["careers"], .15), (["homepage"], .15), (["legal"], .05), (["locations", "contact"], .05)],
}
CONVERT_P = {"booking": .17, "gift": .14, "loyalty": .12, "catering": .14, "newsletter": .10, "blog_read": .006, "browse_menu": .010}
CONVERSION_OF = {"booking": "Table Booked", "gift": "Gift Card Purchased", "loyalty": "Loyalty Signup", "catering": "Catering Enquiry",
                 "newsletter": "Newsletter Signup", "blog_read": "Newsletter Signup", "browse_menu": "Table Booked"}
DWELL_MEDIAN = {"en": 28, "da": 20, "sv": 38, "no": 26}  # seconds between pageviews
DEVICES = ["mobile", "desktop", "tablet"]
WEEKDAY = [0.8, 0.85, 0.95, 1.05, 1.2, 1.15, 1.0]
MONTH = {4: 0.85, 5: 1.0, 6: 1.15, 7: 1.2, 8: 1.1, 9: 0.95, 10: 1.05}
HOURS = [0.2, 0.1, 0.05, 0.05, 0.05, 0.1, 0.3, 0.6, 1.0, 1.4, 1.8, 2.2, 2.4, 2.0, 1.6, 1.5, 1.8, 2.2, 2.6, 2.6, 2.2, 1.6, 0.9, 0.4]

# Research before converting: chance that a converter visited in earlier sessions, and how long before.
# Danish guests mostly book on the spot; Swedish, Norwegian and English-speaking guests come back to book.
# Catering is a considered purchase that takes days.
PRIOR_RESEARCH_P = {
    "Table Booked": {"da": .10, "sv": .55, "no": .50, "en": .40},
    "Catering Enquiry": {"da": .85, "sv": .85, "no": .85, "en": .85},
    "Gift Card Purchased": {"da": .25, "sv": .25, "no": .25, "en": .25},
    "Loyalty Signup": {"da": .20, "sv": .20, "no": .20, "en": .20},
    "Newsletter Signup": {"da": .10, "sv": .10, "no": .10, "en": .10},
}
PRIOR_LAG_HOURS = {  # (median, spread) of a lognormal, in hours before the converting session
    "Table Booked": {"da": (6, 0.8), "sv": (40, 0.7), "no": (36, 0.7), "en": (30, 0.8)},
    "Catering Enquiry": {m: (150, 0.5) for m in MARKETS},
    "Gift Card Purchased": {m: (48, 0.8) for m in MARKETS},
    "Loyalty Signup": {m: (72, 0.8) for m in MARKETS},
    "Newsletter Signup": {m: (96, 0.8) for m in MARKETS},
}
PRIOR_SEQS = {
    "Table Booked": [(["menu_dinner"], .4), (["locations", "menu_dinner"], .35), (["homepage", "menu_lunch"], .25)],
    "Catering Enquiry": [(["catering_events"], .45), (["homepage", "catering_events", "menu_dinner"], .35), (["catering_events", "catering_events"], .20)],
    "Gift Card Purchased": [(["gift_cards"], .6), (["homepage", "gift_cards"], .4)],
    "Loyalty Signup": [(["loyalty"], .5), (["homepage", "menu_dinner"], .5)],
    "Newsletter Signup": [(["blog_chef_stories"], .5), (["homepage"], .5)],
}
PRIOR_CHANNELS = {"organic": .35, "direct": .20, "social": .15, "paid": .10, "ai-referrals": .10, "referrals": .10}


def weighted(options):
    keys, weights = zip(*options)
    return rng.choices(keys, weights=weights)[0]


def channel_weights(d):
    """Channel mix over time: AI referrals grow, social peaks in summer, email peaks before Christmas."""
    progress = (d - START).days / (END - START).days
    w = {"direct": 0.24, "organic": 0.27, "paid": 0.14, "social": 0.12, "email": 0.05, "referrals": 0.12, "ai-referrals": 0.005 + 0.04 * progress}
    if d.month in (6, 7, 8):
        w["social"] *= 1.5
    if d.month == 10:
        w["email"] *= 2.2
    return w


def campaign_active(d):
    if date(2026, 6, 1) <= d <= date(2026, 8, 31):
        return "summer-terrace-2026"
    if d >= date(2026, 10, 5):
        return "christmas-menu-2026"
    return None


def pick_intent(channel, d, market):
    w = dict(INTENT_BY_CHANNEL[channel])
    if d.month == 10:
        w["gift"] = w.get("gift", 0) * 2.5  # gift cards rise towards Christmas
    if campaign_active(d) == "summer-terrace-2026" and channel in ("paid", "social"):
        w["booking"] = w.get("booking", 0) * 1.3
    return rng.choices(list(w), weights=list(w.values()))[0]


def utm_for(channel, d):
    camp = campaign_active(d)
    if channel == "paid":
        return "google", "cpc", camp or "brand-search"
    if channel == "social":
        return rng.choice(["instagram", "facebook", "tiktok"]), "social", camp or "organic-social"
    if channel == "email":
        return "newsletter", "email", camp or "weekly-newsletter"
    return None, None, None


def referrer_for(channel):
    return {"organic": "https://www.google.example/", "referrals": rng.choice(["https://www.tripadvisor.example/", "https://www.foodguide.example/", "https://www.cityblog.example/"]),
            "ai-referrals": rng.choice(["https://chat.assistant.example/", "https://search.ai-engine.example/"]),
            "social": rng.choice(["https://l.instagram.example/", "https://m.facebook.example/", "https://www.tiktok.example/"]),
            "email": "", "direct": "", "paid": "https://www.google.example/"}.get(channel, "")


def session_start(d):
    hour = rng.choices(range(24), weights=HOURS)[0]
    return datetime(d.year, d.month, d.day, hour, rng.randrange(60), rng.randrange(60))


def value_for(ctype):
    if ctype == "Table Booked":
        size = rng.choices([2, 3, 4, 5, 6, 8], weights=[45, 15, 22, 8, 7, 3])[0]
        return size, round(size * 35.0, 2)
    if ctype == "Gift Card Purchased":
        return None, float(rng.choices([50, 100, 150], weights=[50, 35, 15])[0])
    if ctype == "Catering Enquiry":
        return None, float(rng.randrange(600, 3500, 50))
    return None, 0.0


# --------------------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------------------
def simulate():
    rows = []
    visitors = {}  # id -> dict
    returning_pool = []  # (visitor_id, last_day)
    counters = {"event": 0, "session": 0, "conv": 0, "visitor": 0}

    def new_visitor():
        counters["visitor"] += 1
        vid = f"v{counters['visitor']:06d}"
        market = weighted([(m, i["weight"]) for m, i in MARKETS.items()])
        device = rng.choices(DEVICES, weights=[68, 26, 6])[0]
        visitors[vid] = {"market": market, "device": device}
        return vid

    def emit_pageviews(vid, channel, start, seq, city_hint):
        """Append one session's pageviews to rows; return (last row, time after the last pageview)."""
        vis = visitors[vid]
        market = vis["market"]
        counters["session"] += 1
        sid = f"s{counters['session']:07d}"
        utm_source, utm_medium, utm_campaign = utm_for(channel, start.date())
        ref = referrer_for(channel)
        t = start
        prev_path = None
        for i, topic in enumerate(seq):
            if topic == "booking_widget":
                path, title, ctype, funnel, lang, domain = WIDGET_PATH, WIDGET_TITLE, None, "bottom", None, BOOKING_DOMAIN
            else:
                pg = pick_page(topic, market, city_hint)
                path, title, ctype, funnel, lang, domain = pg["path"], pg["title"], pg["content_type"], pg["funnel"], pg["language"], SITE_DOMAIN
            counters["event"] += 1
            rows.append({
                "event_id": f"e{counters['event']:08d}", "event_time": t, "event_type": "pageview", "visitor_id": vid, "session_id": sid,
                "market": MARKETS[market]["label"], "language": lang, "device_type": vis["device"], "visit_source": channel,
                "utm_source": utm_source, "utm_medium": utm_medium, "utm_campaign": utm_campaign,
                "referrer": ref if i == 0 else f"https://{SITE_DOMAIN}{prev_path}",
                "url_domain": domain, "url_path": path, "page_title": title, "content_type": ctype, "content_topic": topic,
                "funnel_stage": funnel, "restaurant_location": next((c for c in CITIES if path.endswith(c.lower())), None),
                "conversion_id": None, "conversion_type": None, "conversion_value_eur": None, "party_size": None,
            })
            prev_path = path
            t = t + timedelta(seconds=max(4, int(rng.lognormvariate(math.log(DWELL_MEDIAN[market]), 0.7))))
        return rows[-1], t

    def emit_prior_research(vid, conv_type, before, city_hint):
        """Earlier research sessions for a converter, placed hours or days before the converting session."""
        market = visitors[vid]["market"]
        if rng.random() >= PRIOR_RESEARCH_P[conv_type][market]:
            return
        n = rng.choices([1, 2, 3], weights=[60, 30, 10])[0] if conv_type == "Catering Enquiry" else rng.choices([1, 2], weights=[80, 20])[0]
        median, spread = PRIOR_LAG_HOURS[conv_type][market]
        t = before
        for _ in range(n):
            t = t - timedelta(hours=max(0.5, rng.lognormvariate(math.log(median), spread)) / n)
            if t.date() < START:
                return
            channel = rng.choices(list(PRIOR_CHANNELS), weights=list(PRIOR_CHANNELS.values()))[0]
            emit_pageviews(vid, channel, t, list(weighted([(tuple(s), w) for s, w in PRIOR_SEQS[conv_type]])), city_hint)

    day = START
    while day <= END:
        n = nrng.poisson(BASE_SESSIONS_PER_DAY * MONTH[day.month] * WEEKDAY[day.weekday()])
        # drop returning visitors not seen for 35 days
        returning_pool = [(v, ld) for v, ld in returning_pool if (day - ld).days <= 35]
        for _ in range(n):
            is_return = returning_pool and rng.random() < 0.22
            if is_return:
                idx = rng.randrange(len(returning_pool))
                vid, _ld = returning_pool[idx]
                returning_pool[idx] = (vid, day)
                cw = {"direct": .55, "organic": .22, "email": .10, "paid": .05, "social": .04, "referrals": .02, "ai-referrals": .02}
            else:
                vid = new_visitor()
                returning_pool.append((vid, day))
                cw = channel_weights(day)
            market = visitors[vid]["market"]
            channel = rng.choices(list(cw), weights=list(cw.values()))[0]
            intent = pick_intent(channel, day, market)
            seq = list(weighted([(tuple(s), w) for s, w in SEQS[intent]]))
            # campaign pages only while a campaign runs; otherwise use the homepage
            camp = campaign_active(day)
            seq = [("homepage" if t == "campaign_landing" and not camp else t) for t in seq]
            # paid / social traffic in campaign periods lands on the campaign page more often
            if camp and channel in ("paid", "social") and seq[0] != "campaign_landing" and rng.random() < 0.45 and intent in ("booking", "browse_menu", "newsletter"):
                seq = ["campaign_landing"] + seq
            # extra browsing noise
            if rng.random() < 0.18:
                seq.insert(rng.randrange(len(seq) + 1), rng.choice(["menu_dinner", "locations", "homepage", "menu_lunch"]))
            will_convert = rng.random() < CONVERT_P.get(intent, 0.0) * (1.15 if is_return else 1.0)
            conv_type = CONVERSION_OF.get(intent) if will_convert else None
            if conv_type == "Table Booked" and intent == "booking":
                seq = seq[:-1] + [rng.choices(["booking", "booking_widget"], weights=[55, 45])[0]]
            elif conv_type == "Table Booked":
                seq = seq + [rng.choices(["booking", "booking_widget"], weights=[55, 45])[0]]
            elif conv_type == "Loyalty Signup" and seq[-1] != "loyalty":
                seq = seq + ["loyalty"]
            elif conv_type == "Gift Card Purchased" and seq[-1] != "gift_cards":
                seq = seq + ["gift_cards"]
            elif conv_type == "Catering Enquiry" and seq[-1] not in ("contact", "catering_events"):
                seq = seq + ["catering_events"]
            # an abandoned conversion intent is simply a session without a conversion
            city_hint = None
            if market in ("da", "sv", "no") and rng.random() < 0.7:
                city_hint = rng.choice([c.lower() for c, o in CITIES.items() if o == market])
            start = session_start(day)
            if conv_type and not is_return:
                emit_prior_research(vid, conv_type, start, city_hint)
            last, t = emit_pageviews(vid, channel, start, seq, city_hint)
            if conv_type:
                counters["conv"] += 1
                party, value = value_for(conv_type)
                loc = last["restaurant_location"]
                if conv_type == "Table Booked" and not loc:
                    loc = (rng.choice([c for c, o in CITIES.items() if o == market]) if market != "en" else rng.choice(list(CITIES)))
                counters["event"] += 1
                rows.append({**last, "event_id": f"e{counters['event']:08d}", "event_time": t + timedelta(seconds=rng.randrange(5, 90)),
                             "event_type": "conversion", "conversion_id": f"c{counters['conv']:06d}", "conversion_type": conv_type,
                             "conversion_value_eur": value, "party_size": party,
                             "restaurant_location": loc if conv_type == "Table Booked" else None})
                # a little browsing after converting
                if rng.random() < 0.2:
                    for _ in range(rng.choice([1, 2])):
                        pg = pick_page(rng.choice(["homepage", "menu_dinner", "locations"]), market)
                        counters["event"] += 1
                        t = t + timedelta(seconds=rng.randrange(20, 200))
                        rows.append({**last, "event_id": f"e{counters['event']:08d}", "event_time": t + timedelta(minutes=2), "event_type": "pageview",
                                     "url_path": pg["path"], "page_title": pg["title"], "content_type": pg["content_type"], "content_topic": pg["topic"],
                                     "funnel_stage": pg["funnel"], "language": pg["language"], "url_domain": SITE_DOMAIN,
                                     "conversion_id": None, "conversion_type": None, "conversion_value_eur": None, "party_size": None,
                                     "restaurant_location": None})
        day += timedelta(days=1)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    df = simulate().sort_values(["event_time", "event_id"]).reset_index(drop=True)
    df["event_time"] = df["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(OUT / "website_events.csv", index=False)
    pv = df[df.event_type == "pageview"]
    cv = df[df.event_type == "conversion"]
    print(f"rows={len(df):,}  pageviews={len(pv):,}  conversions={len(cv):,}  visitors={df.visitor_id.nunique():,}  sessions={df.session_id.nunique():,}")
    print(f"visitor conversion rate: {cv.visitor_id.nunique() / df.visitor_id.nunique():.1%}")


if __name__ == "__main__":
    main()

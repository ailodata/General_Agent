"""Synthetic operations data for a fictional Danish restaurant group ("FORK").

One table, VISITS: one row per table or party (a booking, a walk-in, a cancellation or a no-show), with
the restaurant, the booking, the bill and the costs. It lets an agent answer classic restaurant questions:
revenue, guests, average spend per guest, no-shows by channel, food cost %, labour cost % and prime cost.

Labour is planned per service (restaurant, date, service) and allocated to the completed visits of that
service by number of guests, so sums over any slice give the right labour cost.

Everything here is invented. No real company or customer data is used.

Run:  python data_generator/generate_data.py   -> writes data/visits.csv
"""
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
START = date(2025, 1, 1)
END = date(2026, 10, 25)
OUT = Path(__file__).resolve().parent.parent / "data"

rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)

# --------------------------------------------------------------------------------------
# Restaurants
# --------------------------------------------------------------------------------------
# services: service -> (base parties per day, seat turns); closed: weekdays closed (0 = Monday)
# spend: average spend per guest ex VAT in DKK at 2025 prices; food_cost / bev_cost: share of that revenue
RESTAURANTS = {
    "LIVO": {"concept": "Italian", "city": "Copenhagen", "seats": 90, "closed": [],
             "services": {"lunch": (22, 1.2), "dinner": (40, 1.6)},
             "food": 255, "wine": 95, "other_bev": 55, "food_cost": .25, "bev_cost": .27, "walk_in": .35},
    "VERDE": {"concept": "Plant-based", "city": "Copenhagen", "seats": 60, "closed": [0],
              "services": {"lunch": (14, 1.2), "dinner": (20, 1.5)},
              "food": 235, "wine": 75, "other_bev": 50, "food_cost": .28, "bev_cost": .27, "walk_in": .30},
    "MORGEN": {"concept": "Brunch & café", "city": "Aarhus", "seats": 70, "closed": [],
               "services": {"brunch": (48, 2.0)},
               "food": 165, "wine": 15, "other_bev": 70, "food_cost": .30, "bev_cost": .22, "walk_in": .60},
    "HAVEN": {"concept": "Harbour terrace", "city": "Aarhus", "seats": 130, "closed": [],
              "services": {"lunch": (24, 1.3), "dinner": (34, 1.5)},
              "food": 275, "wine": 110, "other_bev": 70, "food_cost": .30, "bev_cost": .26, "walk_in": .40},
    "BISTRO 33": {"concept": "French bistro", "city": "Odense", "seats": 65, "closed": [6],
                  "services": {"lunch": (14, 1.2), "dinner": (28, 1.5)},
                  "food": 295, "wine": 150, "other_bev": 45, "food_cost": .31, "bev_cost": .28, "walk_in": .20},
    "EMBER": {"concept": "Grill & steak", "city": "Copenhagen", "seats": 80, "closed": [0],
              "services": {"dinner": (42, 1.5)},
              "food": 470, "wine": 190, "other_bev": 70, "food_cost": .32, "bev_cost": .28, "walk_in": .10},
    "MARE": {"concept": "Seafood", "city": "Aalborg", "seats": 70, "closed": [],
             "services": {"dinner": (30, 1.4)},
             "food": 410, "wine": 165, "other_bev": 50, "food_cost": .37, "bev_cost": .28, "walk_in": .15},
}

SERVICE_HOURS = {  # (start hour, end hour, peak hour) for arrival times
    "brunch": (9.0, 14.0, 11.0),
    "lunch": (11.5, 14.5, 12.5),
    "dinner": (17.5, 21.5, 19.0),
}
WEEKDAY = {  # demand by weekday, Monday first
    "brunch": [0.55, 0.55, 0.6, 0.65, 0.8, 1.9, 1.8],
    "lunch": [0.9, 1.0, 1.0, 1.05, 1.15, 1.0, 0.7],
    "dinner": [0.6, 0.7, 0.85, 1.0, 1.45, 1.55, 0.8],
}
# city restaurants dip in the July holiday and peak with Christmas parties in November and December
CITY_MONTH = {1: 0.8, 2: 0.85, 3: 0.95, 4: 1.0, 5: 1.05, 6: 1.05, 7: 0.8, 8: 0.95, 9: 1.0, 10: 1.0, 11: 1.15, 12: 1.3}
HAVEN_MONTH = {1: 0.45, 2: 0.45, 3: 0.6, 4: 0.85, 5: 1.1, 6: 1.6, 7: 1.85, 8: 1.7, 9: 1.0, 10: 0.7, 11: 0.75, 12: 0.95}
MORGEN_MONTH = {1: 0.85, 2: 0.9, 3: 0.95, 4: 1.0, 5: 1.05, 6: 1.05, 7: 1.0, 8: 1.0, 9: 1.0, 10: 1.0, 11: 1.0, 12: 1.1}

CHANNELS = {"website": .50, "phone": .20, "booking_portal": .30}
NO_SHOW = {"website": .035, "phone": .03, "booking_portal": .09}
CANCEL = {"website": .07, "phone": .06, "booking_portal": .11}
PAYMENT = {"card": .78, "mobile_pay": .15, "cash": .03, "invoice": .04}
PRICE_INFLATION = 0.035  # per year
LABOUR_TARGET = 0.30  # planned labour as share of expected revenue
LABOUR_FLOOR = {"brunch": 3800, "lunch": 4600, "dinner": 7800}  # minimum crew per service, DKK


def month_factor(name, d):
    if name == "HAVEN":
        return HAVEN_MONTH[d.month]
    if name == "MORGEN":
        return MORGEN_MONTH[d.month]
    return CITY_MONTH[d.month]


def trend(name, d):
    """Overall growth, plus VERDE growing steadily month by month."""
    months = (d.year - START.year) * 12 + d.month - START.month
    t = 1 + 0.004 * months
    if name == "VERDE":
        t *= 1 + 0.035 * months
    return t


def price_index(d):
    return (1 + PRICE_INFLATION) ** ((d - START).days / 365)


def food_cost_pct(name, d):
    """EMBER's food cost climbs through 2026 as beef prices rise."""
    pct = RESTAURANTS[name]["food_cost"]
    if name == "EMBER" and d >= date(2026, 1, 1):
        pct += 0.055 * min(1.0, (d - date(2026, 1, 1)).days / 290)
    return pct


def staffing_month(name, d):
    """HAVEN staffs up for summer in May and keeps the summer crew through September."""
    if name == "HAVEN" and d.month in (5, 9):
        return HAVEN_MONTH[7] * 0.95
    return month_factor(name, d)


def staffing_weekday(name, service, d):
    """MARE runs a Thursday-sized crew on Mondays and Tuesdays."""
    if name == "MARE" and d.weekday() in (0, 1):
        return WEEKDAY[service][3]
    return WEEKDAY[service][d.weekday()]


def party_size(service, occasion):
    if occasion == "group":
        return rng.choice(range(8, 21))
    if service == "brunch":
        return rng.choices([1, 2, 3, 4, 5, 6], weights=[10, 45, 15, 20, 5, 5])[0]
    return rng.choices([1, 2, 3, 4, 5, 6, 7, 8], weights=[3, 50, 12, 22, 5, 5, 1, 2])[0]


def occasion_for(service, d):
    w = {"none": 70, "birthday": 9, "anniversary": 4, "business": 10 if service == "lunch" else 4, "group": 3}
    if d.month in (11, 12) and service == "dinner":
        w["group"] = 12  # Christmas parties
    return rng.choices(list(w), weights=list(w.values()))[0]


def arrival(d, service):
    lo, hi, peak = SERVICE_HOURS[service]
    h = min(hi, max(lo, rng.triangular(lo, hi, peak)))
    minute = int(round((h % 1) * 60 / 15) * 15)
    return datetime(d.year, d.month, d.day, int(h)) + timedelta(minutes=minute)


def lead_time(occasion, d):
    """Days between booking and visit."""
    median = {"group": 21, "anniversary": 10, "birthday": 8, "business": 3, "none": 2.5}[occasion]
    if d.month in (11, 12) and occasion == "group":
        median = 35
    return max(0.05, rng.lognormvariate(math.log(median), 0.9))


# --------------------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------------------
def simulate():
    rows = []
    counters = {"visit": 0, "booking": 0}
    d = START
    while d <= END:
        for name, r in RESTAURANTS.items():
            if d.weekday() in r["closed"]:
                continue
            if d.month == 12 and d.day in (24, 25, 31) or d.month == 1 and d.day == 1:
                continue
            for service, (base, turns) in r["services"].items():
                capacity = r["seats"] * turns
                expected = base * WEEKDAY[service][d.weekday()] * month_factor(name, d) * trend(name, d)
                n = nrng.poisson(expected * rng.uniform(0.85, 1.15))
                visits = []
                for _ in range(n):
                    walk_in = rng.random() < r["walk_in"]
                    occasion = "none" if walk_in else occasion_for(service, d)
                    v = {"restaurant": name, "service": service, "occasion": occasion,
                         "guests": party_size(service, occasion), "time": arrival(d, service)}
                    if walk_in:
                        v.update(channel="walk_in", status="completed", booking_id=None, booked_at=None)
                    else:
                        channel = rng.choices(list(CHANNELS), weights=list(CHANNELS.values()))[0]
                        roll = rng.random()
                        status = "no_show" if roll < NO_SHOW[channel] else "cancelled" if roll < NO_SHOW[channel] + CANCEL[channel] else "completed"
                        counters["booking"] += 1
                        booked_at = v["time"] - timedelta(days=lead_time(occasion, d))
                        v.update(channel=channel, status=status, booking_id=f"B{counters['booking']:07d}",
                                 booked_at=booked_at.replace(second=0, microsecond=0))
                    visits.append(v)

                # walk-ins are turned away once the service is full
                covers = 0
                kept = []
                for v in sorted(visits, key=lambda v: v["channel"] == "walk_in"):
                    if v["status"] == "completed":
                        if v["channel"] == "walk_in" and covers + v["guests"] > capacity:
                            continue
                        covers += v["guests"]
                    kept.append(v)
                busy = covers / capacity

                # bill per completed visit
                pi = price_index(d)
                fc_pct = food_cost_pct(name, d)
                # wine sales per guest drop on the busiest services
                wine_factor = 1 - 0.45 * max(0.0, min(1.0, (busy - 0.7) / 0.3))
                for v in kept:
                    if v["status"] != "completed":
                        continue
                    g = v["guests"]
                    uplift = {"anniversary": 1.25, "birthday": 1.1, "business": 1.15, "group": 0.9}.get(v["occasion"], 1.0)
                    food = g * r["food"] * pi * uplift * rng.lognormvariate(0, 0.18)
                    wine = g * r["wine"] * pi * uplift * wine_factor * rng.lognormvariate(0, 0.45) * (rng.random() < 0.8)
                    other = g * r["other_bev"] * pi * rng.lognormvariate(0, 0.3)
                    v.update(food=round(food, 2), wine=round(wine, 2), other=round(other, 2),
                             food_cost=round(food * fc_pct * rng.lognormvariate(0, 0.05), 2),
                             bev_cost=round((wine + other) * r["bev_cost"] * rng.lognormvariate(0, 0.05), 2),
                             tip=round((food + wine + other) * 1.25 * rng.choice([0, 0, 0.03, 0.05, 0.08, 0.1]), 2),
                             payment=("invoice" if v["occasion"] in ("business", "group") and rng.random() < 0.5
                                      else rng.choices(list(PAYMENT), weights=list(PAYMENT.values()))[0]))

                # labour: planned from the staffing forecast, then allocated to completed visits by guests
                planned_parties = base * staffing_weekday(name, service, d) * staffing_month(name, d) * trend(name, d)
                avg_party = 2.6 if service != "brunch" else 2.5
                planned_revenue = planned_parties * avg_party * (r["food"] + r["wine"] + r["other_bev"]) * pi
                labour = max(LABOUR_FLOOR[service] * pi, planned_revenue * LABOUR_TARGET) * rng.lognormvariate(0, 0.06)
                for v in kept:
                    if v["status"] == "completed":
                        v["labour"] = round(labour * v["guests"] / covers, 2)
                    rows.append(v)
        d += timedelta(days=1)

    rows.sort(key=lambda v: (v["time"], v["restaurant"]))
    out = []
    for v in rows:
        counters["visit"] += 1
        done = v["status"] == "completed"
        out.append({
            "visit_id": f"V{counters['visit']:07d}",
            "restaurant": v["restaurant"],
            "concept": RESTAURANTS[v["restaurant"]]["concept"],
            "city": RESTAURANTS[v["restaurant"]]["city"],
            "visit_date": v["time"].date().isoformat(),
            "visit_time": v["time"].strftime("%H:%M"),
            "service": v["service"],
            "guests": v["guests"],
            "status": v["status"],
            "booking_channel": v["channel"],
            "booking_id": v["booking_id"],
            "booked_at": v["booked_at"].strftime("%Y-%m-%d %H:%M:%S") if v["booked_at"] else None,
            "occasion": v["occasion"],
            "food_revenue": v["food"] if done else None,
            "wine_revenue": v["wine"] if done else None,
            "other_beverage_revenue": v["other"] if done else None,
            "total_revenue": round(v["food"] + v["wine"] + v["other"], 2) if done else None,
            "tip": v["tip"] if done else None,
            "payment_method": v["payment"] if done else None,
            "food_cost": v["food_cost"] if done else None,
            "beverage_cost": v["bev_cost"] if done else None,
            "labour_cost": v["labour"] if done else None,
        })
    return pd.DataFrame(out)


def main():
    OUT.mkdir(exist_ok=True)
    df = simulate()
    df.to_csv(OUT / "visits.csv", index=False)
    done = df[df.status == "completed"]
    print(f"rows={len(df):,}  completed={len(done):,}  guests={done.guests.sum():,}  "
          f"revenue={done.total_revenue.sum() / 1e6:,.1f}m DKK  {df.visit_date.min()} to {df.visit_date.max()}")


if __name__ == "__main__":
    main()

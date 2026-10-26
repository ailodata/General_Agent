"""Check that the built-in demo findings are present in data/visits.csv.

Run after generate_data.py:  python data_generator/check_findings.py
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "visits.csv"

df = pd.read_csv(DATA, parse_dates=["visit_date"])
done = df[df.status == "completed"].copy()
done["month"] = done.visit_date.dt.to_period("M")
pct = lambda s: s.map("{:.1%}".format)


def kpis(g):
    rev = g.total_revenue.sum()
    return pd.Series({
        "revenue_m": round(rev / 1e6, 2),
        "guests": g.guests.sum(),
        "spend_per_guest": round(rev / g.guests.sum()),
        "food_cost_pct": g.food_cost.sum() / g.food_revenue.sum(),
        "labour_pct": g.labour_cost.sum() / rev,
        "prime_cost_pct": (g.food_cost.sum() + g.beverage_cost.sum() + g.labour_cost.sum()) / rev,
        "wine_per_guest": round(g.wine_revenue.sum() / g.guests.sum()),
    })


print(f"rows={len(df):,}  completed={len(done):,}\n")

print("1. Per restaurant")
per = done.groupby("restaurant").apply(kpis, include_groups=False)
print(per.to_string(formatters={c: "{:.1%}".format for c in ["food_cost_pct", "labour_pct", "prime_cost_pct"]}), "\n")

print("2. No-show rate by booking channel")
booked = df[df.booking_channel != "walk_in"]
print(pct(booked.groupby("booking_channel").status.apply(lambda s: (s == "no_show").mean())).to_string(), "\n")

print("3. HAVEN labour % by month (2025)")
h = done[(done.restaurant == "HAVEN") & (done.visit_date.dt.year == 2025)]
print(pct(h.groupby(h.visit_date.dt.month).apply(lambda g: g.labour_cost.sum() / g.total_revenue.sum(), include_groups=False)).to_string(), "\n")

print("4. MARE labour % by weekday (0 = Monday)")
m = done[done.restaurant == "MARE"]
print(pct(m.groupby(m.visit_date.dt.weekday).apply(lambda g: g.labour_cost.sum() / g.total_revenue.sum(), include_groups=False)).to_string(), "\n")

print("5. VERDE guests per month (first and last 3)")
v = done[done.restaurant == "VERDE"].groupby("month").guests.sum()
print(pd.concat([v.head(3), v.tail(3)]).to_string(), "\n")

print("6. EMBER food cost % by quarter")
e = done[done.restaurant == "EMBER"]
print(pct(e.groupby(e.visit_date.dt.to_period("Q")).apply(lambda g: g.food_cost.sum() / g.food_revenue.sum(), include_groups=False)).to_string(), "\n")

print("7. Wine per guest by how full the service was (dinner)")
d = done[done.service == "dinner"]
svc = d.groupby(["restaurant", "visit_date"]).agg(guests=("guests", "sum"), wine=("wine_revenue", "sum")).reset_index()
svc["fullness"] = svc.groupby("restaurant").guests.transform(lambda s: pd.qcut(s, 4, labels=["quietest", "q2", "q3", "busiest"]))
print(svc.groupby("fullness", observed=True).apply(lambda g: round(g.wine.sum() / g.guests.sum()), include_groups=False).to_string(), "\n")

print("8. Year over year, Jan-Oct revenue (m DKK)")
ytd = done[done.visit_date.dt.month <= 10]
print((ytd.groupby(ytd.visit_date.dt.year).total_revenue.sum() / 1e6).round(1).to_string())

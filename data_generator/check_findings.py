"""Check that the built-in demo findings are present in data/website_events.csv.

Run after generate_data.py:  python data_generator/check_findings.py
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "website_events.csv"

df = pd.read_csv(DATA, parse_dates=["event_time"])
pv = df[df.event_type == "pageview"]
cv = df[df.event_type == "conversion"]
converters = set(cv.visitor_id)
overall = len(converters) / df.visitor_id.nunique()
print(f"Overall visitor conversion rate: {overall:.1%}\n")


def visitor_rate(visitor_ids):
    visitor_ids = set(visitor_ids)
    return len(visitor_ids & converters) / len(visitor_ids)


print("1. AI referrals grow (share of sessions by month)")
first = df.sort_values("event_time").groupby("session_id").first()
share = first.groupby(first.event_time.dt.to_period("M")).visit_source.apply(lambda s: (s == "ai-referrals").mean())
print(share.map("{:.1%}".format).to_string(), "\n")

print("2. Conversion rate per session by channel")
conv_sessions = set(cv.session_id)
by_channel = first.groupby("visit_source").apply(lambda g: g.index.isin(list(conv_sessions)).mean(), include_groups=False)
print(by_channel.sort_values().map("{:.1%}".format).to_string(), "\n")

print("3. Content: share of pageviews vs visitor conversion rate by topic")
topic = pv.groupby("content_topic").agg(pageviews=("event_id", "count"), visitors=("visitor_id", "nunique"))
topic["share_of_pageviews"] = topic.pageviews / len(pv)
topic["visitor_conversion_rate"] = [visitor_rate(pv[pv.content_topic == t].visitor_id) for t in topic.index]
print(topic.sort_values("pageviews", ascending=False).head(10).to_string(
    formatters={"share_of_pageviews": "{:.1%}".format, "visitor_conversion_rate": "{:.1%}".format}), "\n")

print("4. Time to convert (first visit -> conversion), median hours")
first_seen = df.groupby("visitor_id").event_time.min()
cv = cv.assign(hours=(cv.event_time - cv.visitor_id.map(first_seen)).dt.total_seconds() / 3600)
print(cv[cv.conversion_type == "Table Booked"].groupby("market").hours.median().round(1).to_string())
print(cv.groupby("conversion_type").hours.median().round(1).to_string(), "\n")

print("5. Gift cards per month")
gifts = cv[cv.conversion_type == "Gift Card Purchased"]
print(gifts.groupby(gifts.event_time.dt.to_period("M")).size().to_string(), "\n")

print("6. Campaign page viewers vs everyone")
camp_visitors = pv[pv.content_topic == "campaign_landing"].visitor_id
print(f"campaign viewers: {visitor_rate(camp_visitors):.1%}  vs overall {overall:.1%}")

# General_Agent

A demo of AILO's analytics agent, built on **synthetic data**, for sales and marketing.

The agent lets people ask questions about their business in plain language, such as *"Which restaurant has the highest labour cost?"*, *"How many no-shows do we get from the booking portal?"* or *"How has food cost developed at EMBER this year?"*. It answers with numbers, tables and charts. The demo is the same kind of agent we build for clients, but runs on invented data so it can be shown to anyone.

**No real company or customer data is used anywhere in this repo.**

## The case: FORK

FORK is a fictional Danish restaurant group with seven restaurants:

| Restaurant | Concept | City | Services |
|---|---|---|---|
| LIVO | Italian | Copenhagen | lunch, dinner |
| VERDE | Plant-based | Copenhagen | lunch, dinner (closed Mondays) |
| MORGEN | Brunch & café | Aarhus | brunch |
| HAVEN | Harbour terrace | Aarhus | lunch, dinner |
| BISTRO 33 | French bistro | Odense | lunch, dinner (closed Sundays) |
| EMBER | Grill & steak | Copenhagen | dinner (closed Mondays) |
| MARE | Seafood | Aalborg | dinner |

The data covers 2 January 2025 to 25 October 2026: about 191,000 visits, of which 173,000 were completed, with 572,000 guests and about DKK 259 million in revenue. All restaurants are closed on 24, 25 and 31 December and 1 January.

## The table: `VISITS`

One row per table or party: a booking, a walk-in, a cancellation or a no-show. Amounts are in DKK ex VAT and are only filled in for completed visits.

| Group | Columns |
|---|---|
| Restaurant | `RESTAURANT`, `CONCEPT`, `CITY` |
| Visit | `VISIT_ID`, `VISIT_DATE`, `VISIT_TIME`, `SERVICE` (brunch, lunch, dinner), `GUESTS`, `STATUS` (completed, cancelled, no_show) |
| Booking | `BOOKING_CHANNEL` (website, phone, booking_portal, walk_in), `BOOKING_ID`, `BOOKED_AT`, `OCCASION` (none, birthday, anniversary, business, group) |
| Sales | `FOOD_REVENUE`, `WINE_REVENUE`, `OTHER_BEVERAGE_REVENUE`, `TOTAL_REVENUE`, `TIP`, `PAYMENT_METHOD` |
| Costs | `FOOD_COST`, `BEVERAGE_COST`, `LABOUR_COST` |

Key figures the agent can calculate:

- **Average spend per guest** = `SUM(TOTAL_REVENUE) / SUM(GUESTS)` for completed visits
- **No-show rate** = no-shows / bookings (walk-ins excluded)
- **Food cost %** = `SUM(FOOD_COST) / SUM(FOOD_REVENUE)`
- **Labour cost %** = `SUM(LABOUR_COST) / SUM(TOTAL_REVENUE)`
- **Prime cost %** = (food cost + beverage cost + labour cost) / total revenue

**About labour cost:** labour is planned per service (restaurant, date and service) and allocated to the completed visits in that service by number of guests. Sums over any slice (a day, a month, a restaurant) therefore give the right labour cost, but the table cannot say how many people worked or who was ill.

### Built-in findings

The data has patterns the demo can uncover. `data_generator/check_findings.py` confirms they are present:

1. **EMBER has the highest spend per guest** (about DKK 680), MORGEN the lowest (about DKK 260).
2. **MARE has the highest food cost** (about 37%, seafood is expensive) and **LIVO the lowest** (about 25%).
3. **EMBER's food cost is climbing**: from 32% through 2025 to about 37% by autumn 2026 (beef prices).
4. **HAVEN is overstaffed in May and September**: the summer crew starts too early and stays too long, so labour cost is above 40% in those months against about 30% the rest of the season.
5. **MARE is overstaffed on Mondays and Tuesdays**: labour cost is about 46% on Mondays against about 30% the rest of the week.
6. **The booking portal has the most no-shows**: about 9%, against 3–4% for the website and phone.
7. **VERDE is growing**: guests per month are up about 60% from early 2025 to autumn 2026.
8. **Wine sales drop when it's busy**: wine per guest at dinner is about DKK 120 on the quietest services and about DKK 70 on the busiest.
9. **The group is growing**: revenue from 1 January to 25 October is up about 9% from 2025 to 2026.

Seasonality is built in too: HAVEN is busiest in summer, the city restaurants dip in July and peak with Christmas parties in November and December, and MORGEN is busiest at weekends.

## Repo structure

```
data_generator/   generate_data.py (creates the data) and check_findings.py (verifies the findings)
data/             generated CSV (not committed; recreate it with the generator)
snowflake/        SQL to set up the database, role, warehouse and table, and to load the data
agent/            semantic view YAML, agent instructions, sample questions and build_sql.py
app/              Streamlit frontend (coming)
```

## Getting started

1. **Generate the data**

   ```bash
   pip install -r requirements.txt
   python data_generator/generate_data.py
   python data_generator/check_findings.py
   ```

   The generator is seeded, so it produces the same data every time.

2. **Set up Snowflake**: run `snowflake/01_setup.sql` in a Snowsight worksheet (replace `<YOUR_USER>` first). It creates a small warehouse with a monthly credit cap, the database `GENERAL_AGENT_DEMO`, the schema `RESTAURANT`, the role `GENERAL_AGENT_ROLE` and the table `VISITS`.

3. **Load the data**: follow `snowflake/02_load_data.sql` (Snowsight upload or `PUT`/`COPY`) and run the checks at the bottom.

4. **Create the semantic view**: follow `snowflake/03_semantic_view.sql` to create `FORK_VISITS_SEMANTIC` from `agent/fork_visits_semantic.yaml` (upload in Snowsight or paste into SQL), then grant it to `GENERAL_AGENT_ROLE`.

5. **Create the agent**: run `snowflake/04_agent.sql`. It creates `FORK_AGENT` with the semantic view as its tool and grants it to `GENERAL_AGENT_ROLE`.

The SQL files in step 4 and 5 are generated. Edit the files in `agent/` and run `python agent/build_sql.py` to rebuild them.

## Status

- [x] Synthetic data and findings
- [x] Snowflake setup and loading SQL
- [x] Semantic view
- [x] Agent instructions and agent
- [ ] Streamlit app with configurable branding
- [ ] Deploy
- [ ] Testing and demo material (script, example questions, screenshots)

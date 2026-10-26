# General_Agent

A demo of AILO's marketing analytics agent, built on **synthetic data**, for sales and marketing.

The agent lets marketing people ask questions about their website in plain language, such as *"Which channels convert best?"*, *"What content drives bookings?"* or *"How long do Swedish guests take to book?"*. It answers with numbers, tables and charts. The demo is the same kind of agent we build for clients, but runs on invented data so it can be shown to anyone.

**No real company or customer data is used anywhere in this repo.**

## The case: Bistro Lind

Bistro Lind is a fictional Nordic restaurant chain with six restaurants (Copenhagen, Aarhus, Stockholm, Gothenburg, Oslo, Bergen) and a website in English, Danish, Swedish and Norwegian. The data covers 1 April to 18 October 2026: about 93,000 pageviews, 3,300 conversions, 33,000 visitors and 43,000 sessions.

Visitors can convert in five ways:

| Conversion | Value |
|---|---|
| Table Booked | party size × €35 |
| Gift Card Purchased | €50, €100 or €150 |
| Catering Enquiry | estimated €600–3,500 |
| Loyalty Signup (Lind Club) | none |
| Newsletter Signup | none |

Table bookings happen either on the site or in an external booking widget on its own domain without a language.

### Built-in findings

The data has patterns the demo can uncover. `data_generator/check_findings.py` confirms they are present:

1. **AI referrals are growing**: from about 1% of sessions in April to about 4% in October.
2. **Social brings traffic but converts worst** (about 4% of sessions). Paid and email convert best (about 11%).
3. **Recipes pull traffic but don't convert**: recipe posts are the most read content after the core pages, but only about 5% of their readers convert, against about 10% overall.
4. **Danish guests book on the spot**: the median time from first visit to a table booking is minutes for Danish visitors and about a day for Swedish, Norwegian and English-speaking visitors.
5. **Catering takes about a week** from first visit to enquiry.
6. **Gift cards rise towards Christmas**, helped by email in October.
7. **Campaign pages work**: visitors who saw the summer terrace or Christmas menu campaign convert about 15% against about 10% overall.

## Repo structure

```
data_generator/   generate_data.py (creates the data) and check_findings.py (verifies the findings)
data/             generated CSV (not committed; recreate it with the generator)
snowflake/        SQL to set up the database, role, warehouse and table, and to load the data
agent/            semantic view and agent instructions (coming)
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

2. **Set up Snowflake**: run `snowflake/01_setup.sql` in a Snowsight worksheet (replace `<YOUR_USER>` first). It creates a small warehouse with a monthly credit cap, the database `GENERAL_AGENT_DEMO`, the schema `RESTAURANT`, the role `GENERAL_AGENT_ROLE` and the table `WEBSITE_EVENTS`.

3. **Load the data**: follow `snowflake/02_load_data.sql` (Snowsight upload or `PUT`/`COPY`) and run the checks at the bottom.

## Status

- [x] Synthetic data and findings
- [x] Snowflake setup and loading SQL
- [ ] Semantic view
- [ ] Agent instructions and agent
- [ ] Streamlit app with configurable branding
- [ ] Deploy
- [ ] Testing and demo material (script, example questions, screenshots)

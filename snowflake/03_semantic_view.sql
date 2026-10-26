-- Create the semantic view GENERAL_AGENT_DEMO.RESTAURANT.FORK_VISITS_SEMANTIC.
-- The YAML below is a copy of agent/fork_visits_semantic.yaml. If you change that file, paste it in here again.
-- Run the whole worksheet as the role that owns the schema GENERAL_AGENT_DEMO.RESTAURANT.
-- The CALL validates the YAML and fails with an error message if something is wrong.

USE WAREHOUSE GENERAL_AGENT_WH;

CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'GENERAL_AGENT_DEMO.RESTAURANT',
  $$
name: FORK_VISITS_SEMANTIC
description: "Bookings, guests, sales and costs for FORK, a Danish restaurant group with seven restaurants (LIVO, VERDE, MORGEN, HAVEN, BISTRO 33, EMBER, MARE). One row per table or party: a completed visit, a cancelled booking or a no-show. Use this view for revenue, guests, average spend per guest, bookings, no-shows and cancellations, booking channels, food cost %, beverage cost %, labour cost % and prime cost %, per restaurant, city, concept, service and period. All amounts are in DKK ex VAT. The data is synthetic and covers 2 January 2025 to 25 October 2026."
tables:
  - name: VISITS
    description: "One row per table or party. STATUS = 'completed' means the guests came and paid; 'cancelled' and 'no_show' are bookings where the guests did not come, so their amounts are empty. Walk-ins have BOOKING_CHANNEL = 'walk_in' and no booking. A restaurant with no rows on a day was closed."
    base_table:
      database: GENERAL_AGENT_DEMO
      schema: RESTAURANT
      table: VISITS
    primary_key:
      columns:
        - VISIT_ID
    dimensions:
      - name: VISIT_ID
        synonyms:
          - Visit
          - Table id
        description: Unique id for the visit (one table or party).
        expr: VISIT_ID
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - V0000001
          - V0104522
      - name: RESTAURANT
        synonyms:
          - Restaurant name
          - Venue
          - Location
          - Outlet
        description: "The restaurant in the group: LIVO, VERDE, MORGEN, HAVEN, BISTRO 33, EMBER or MARE. Names are written in capitals, and BISTRO 33 has a space."
        expr: RESTAURANT
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - LIVO
          - VERDE
          - MORGEN
          - HAVEN
          - BISTRO 33
          - EMBER
          - MARE
      - name: CONCEPT
        synonyms:
          - Cuisine
          - Restaurant type
        description: "The restaurant's concept: Italian (LIVO), Plant-based (VERDE), Brunch & café (MORGEN), Harbour terrace (HAVEN), French bistro (BISTRO 33), Grill & steak (EMBER), Seafood (MARE)."
        expr: CONCEPT
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - Italian
          - Seafood
          - Grill & steak
      - name: CITY
        synonyms:
          - Town
        description: "City of the restaurant: Copenhagen (LIVO, VERDE, EMBER), Aarhus (MORGEN, HAVEN), Odense (BISTRO 33), Aalborg (MARE)."
        expr: CITY
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - Copenhagen
          - Aarhus
          - Odense
          - Aalborg
      - name: VISIT_TIME
        synonyms:
          - Arrival time
          - Time of booking
        description: Arrival time of the party (or the booked time for cancellations and no-shows), in 15-minute steps.
        expr: VISIT_TIME
        data_type: TIME(9)
        access_modifier: public_access
        sample_values:
          - "12:30:00"
          - "19:00:00"
      - name: SERVICE
        synonyms:
          - Sitting
          - Meal period
          - Shift
        description: "The service: brunch (only MORGEN), lunch or dinner. EMBER and MARE only serve dinner."
        expr: SERVICE
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - brunch
          - lunch
          - dinner
      - name: STATUS
        synonyms:
          - Visit status
          - Booking status
          - Outcome
        description: "completed (guests came and paid), cancelled (booking cancelled in advance) or no_show (booked but did not come)."
        expr: STATUS
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - completed
          - cancelled
          - no_show
      - name: BOOKING_CHANNEL
        synonyms:
          - Channel
          - Booking source
          - Reservation channel
        description: "How the table was booked: website (own website), phone, booking_portal (third-party booking portal) or walk_in (no booking)."
        expr: BOOKING_CHANNEL
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - website
          - phone
          - booking_portal
          - walk_in
      - name: BOOKING_ID
        synonyms:
          - Reservation id
        description: Unique booking id. Empty for walk-ins.
        expr: BOOKING_ID
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - B0000063
          - B0051234
      - name: OCCASION
        synonyms:
          - Reason for visit
          - Event type
        description: "Occasion given on the booking: none, birthday, anniversary, business or group (8 or more guests, many of them Christmas parties in November and December). Always 'none' for walk-ins."
        expr: OCCASION
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - none
          - birthday
          - business
          - group
      - name: PAYMENT_METHOD
        synonyms:
          - Payment type
          - Tender
        description: "How the bill was paid: card, mobile_pay, cash or invoice. Empty unless STATUS = 'completed'."
        expr: PAYMENT_METHOD
        data_type: VARCHAR(16777216)
        access_modifier: public_access
        sample_values:
          - card
          - mobile_pay
          - invoice
    time_dimensions:
      - name: VISIT_DATE
        synonyms:
          - Date
          - Day
          - Service date
        description: "Date of the visit (or of the booked visit for cancellations and no-shows). Use this for all period questions: days, weeks, months, quarters, years and weekdays."
        expr: VISIT_DATE
        data_type: DATE
        access_modifier: public_access
        sample_values:
          - "2025-01-02"
          - "2026-10-25"
      - name: BOOKED_AT
        synonyms:
          - Booking time
          - Reservation made at
        description: When the booking was made. Empty for walk-ins. Used to calculate how far in advance guests book (lead time).
        expr: BOOKED_AT
        data_type: TIMESTAMP_NTZ(9)
        access_modifier: public_access
        sample_values:
          - "2024-12-26 22:20:00"
          - "2026-06-03 14:05:00"
    facts:
      - name: GUESTS
        synonyms:
          - Covers
          - Party size
          - Pax
        description: Number of guests in the party. Also filled for cancellations and no-shows (the booked party size).
        expr: GUESTS
        data_type: NUMBER(3,0)
        access_modifier: public_access
        sample_values:
          - "2"
          - "4"
      - name: FOOD_REVENUE
        synonyms:
          - Food sales
          - Kitchen revenue
        description: Food sales in DKK ex VAT. Empty unless STATUS = 'completed'.
        expr: FOOD_REVENUE
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: WINE_REVENUE
        synonyms:
          - Wine sales
        description: Wine sales in DKK ex VAT. Empty unless STATUS = 'completed'.
        expr: WINE_REVENUE
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: OTHER_BEVERAGE_REVENUE
        synonyms:
          - Other drinks sales
          - Beer, cocktails, soft drinks and coffee
        description: Sales of beer, cocktails, soft drinks and coffee in DKK ex VAT. Empty unless STATUS = 'completed'.
        expr: OTHER_BEVERAGE_REVENUE
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: TOTAL_REVENUE
        synonyms:
          - Revenue
          - Sales
          - Turnover
          - Bill
        description: Food + wine + other beverages in DKK ex VAT. Tips are not included. Empty unless STATUS = 'completed'.
        expr: TOTAL_REVENUE
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: TIP
        synonyms:
          - Gratuity
          - Tips
        description: Tip in DKK. Not part of revenue. Empty unless STATUS = 'completed'.
        expr: TIP
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: FOOD_COST
        synonyms:
          - Cost of food
          - Food COGS
          - Raw material cost
        description: Cost of goods for the food on the bill, in DKK. Empty unless STATUS = 'completed'.
        expr: FOOD_COST
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: BEVERAGE_COST
        synonyms:
          - Cost of drinks
          - Beverage COGS
        description: Cost of goods for wine and other beverages on the bill, in DKK. Empty unless STATUS = 'completed'.
        expr: BEVERAGE_COST
        data_type: NUMBER(12,2)
        access_modifier: public_access
      - name: LABOUR_COST
        synonyms:
          - Staff cost
          - Wage cost
          - Payroll
        description: "Labour cost in DKK. Labour is planned per service (restaurant, date and service) and allocated to the completed visits in that service by number of guests, so sums over any slice give the right labour cost. It cannot be used to count staff or hours. Empty unless STATUS = 'completed'."
        expr: LABOUR_COST
        data_type: NUMBER(12,2)
        access_modifier: public_access
    metrics:
      - name: REVENUE
        synonyms:
          - Total sales
          - Turnover
        description: Total revenue in DKK ex VAT.
        expr: SUM(TOTAL_REVENUE)
        access_modifier: public_access
      - name: COMPLETED_GUESTS
        synonyms:
          - Guests served
          - Covers
        description: Number of guests on completed visits.
        expr: SUM(CASE WHEN STATUS = 'completed' THEN GUESTS END)
        access_modifier: public_access
      - name: COMPLETED_VISITS
        synonyms:
          - Tables served
          - Parties
        description: Number of completed visits (tables or parties).
        expr: COUNT_IF(STATUS = 'completed')
        access_modifier: public_access
      - name: SPEND_PER_GUEST
        synonyms:
          - Average spend per guest
          - Average check per cover
        description: Average revenue per guest in DKK ex VAT, completed visits only.
        expr: SUM(TOTAL_REVENUE) / NULLIF(SUM(CASE WHEN STATUS = 'completed' THEN GUESTS END), 0)
        access_modifier: public_access
      - name: NO_SHOW_RATE_PCT
        synonyms:
          - No-show rate
        description: No-shows as a percentage of bookings (walk-ins excluded).
        expr: ROUND(100.0 * COUNT_IF(STATUS = 'no_show' AND BOOKING_CHANNEL <> 'walk_in') / NULLIF(COUNT_IF(BOOKING_CHANNEL <> 'walk_in'), 0), 1)
        access_modifier: public_access
      - name: FOOD_COST_PCT
        synonyms:
          - Food cost percentage
          - Kitchen cost %
        description: Food cost as a percentage of food revenue.
        expr: ROUND(100.0 * SUM(FOOD_COST) / NULLIF(SUM(FOOD_REVENUE), 0), 1)
        access_modifier: public_access
      - name: LABOUR_COST_PCT
        synonyms:
          - Labour cost percentage
          - Staff cost %
          - Wage %
        description: Labour cost as a percentage of total revenue.
        expr: ROUND(100.0 * SUM(LABOUR_COST) / NULLIF(SUM(TOTAL_REVENUE), 0), 1)
        access_modifier: public_access
      - name: PRIME_COST_PCT
        synonyms:
          - Prime cost percentage
        description: Food cost + beverage cost + labour cost as a percentage of total revenue.
        expr: ROUND(100.0 * (SUM(FOOD_COST) + SUM(BEVERAGE_COST) + SUM(LABOUR_COST)) / NULLIF(SUM(TOTAL_REVENUE), 0), 1)
        access_modifier: public_access
module_custom_instructions:
  sql_generation: |-
    All amounts are in DKK ex VAT. Revenue, tips and costs are only filled in on completed visits (STATUS = 'completed'), so sums are automatically limited to completed visits. Tips are never part of revenue.

    Count guests and visits on completed visits only (STATUS = 'completed'), unless the question is about bookings, cancellations or no-shows. GUESTS is also filled on cancellations and no-shows, so SUM(GUESTS) without the status filter overstates the guests served.

    Average spend per guest is SUM(TOTAL_REVENUE) / SUM(GUESTS) on completed visits. Average bill per table is SUM(TOTAL_REVENUE) / COUNT(*) on completed visits. Always divide sums; never average a per-row ratio.

    Food cost % = SUM(FOOD_COST) / SUM(FOOD_REVENUE). Beverage cost % = SUM(BEVERAGE_COST) / (SUM(WINE_REVENUE) + SUM(OTHER_BEVERAGE_REVENUE)). Labour cost % = SUM(LABOUR_COST) / SUM(TOTAL_REVENUE). Prime cost % = (SUM(FOOD_COST) + SUM(BEVERAGE_COST) + SUM(LABOUR_COST)) / SUM(TOTAL_REVENUE). "Kitchen cost" or "køkkenprocent" means food cost %. "Cost of goods" or "vareforbrug" means food cost + beverage cost.

    LABOUR_COST is the labour of a service allocated to its completed visits by guests. Always sum it; never average it per row, and never use it to count staff, hours or shifts.

    No-show rate = no-shows / bookings, and cancellation rate = cancellations / bookings, where bookings are rows with BOOKING_CHANNEL <> 'walk_in'. Walk-ins are never no-shows or cancellations and must be excluded from the denominator.

    Lead time (how far in advance guests book) = DATEDIFF('minute', BOOKED_AT, TIMESTAMP_NTZ_FROM_PARTS(VISIT_DATE, VISIT_TIME)) / 1440.0 in days, for rows with a booking. Report the median as well as the average, because a few large group bookings are made weeks ahead.

    Express every share, rate and percentage as a value between 0 and 100, rounded to 1 decimal with ROUND(100.0 * numerator / NULLIF(denominator, 0), 1). Never return a fraction between 0 and 1. Name these columns with a _PCT suffix. Round DKK amounts to whole kroner.

    The data ends on 25 October 2026. Interpret relative periods ("this year", "last month", "the last 3 months", "this week") relative to the latest VISIT_DATE in the data, not CURRENT_DATE. "This year" is 2026 and "last year" is 2025. October 2026 is a partial month (up to the 25th).

    When comparing 2026 with 2025, compare the same period in both years (1 January to 25 October), because 2026 is not complete. Say which period the comparison covers.

    A restaurant with no rows on a date was closed that day (VERDE and EMBER close on Mondays, BISTRO 33 on Sundays, and all restaurants close on 24, 25 and 31 December and 1 January). For averages per day, divide by the number of distinct dates the restaurant had visits, not by calendar days.

    For weekday analysis use DAYNAME(VISIT_DATE) and order Monday to Sunday with DAYOFWEEKISO(VISIT_DATE). For monthly trends use DATE_TRUNC('month', VISIT_DATE).

    Restaurant names are in capitals; filter with RESTAURANT = 'EMBER', and 'BISTRO 33' includes a space. If the user writes a restaurant name in lower case or without the space, map it to the exact value.
  question_categorization: |-
    This is synthetic demo data for a fictional restaurant group, FORK. If asked whether the data is real, say it is invented for demonstration purposes.

    The data has one row per table or party with sales split into food, wine and other beverages. It cannot answer questions about individual dishes or menu items, staff counts, hours worked, sick leave or individual employees, table numbers, guest names or reviews, weather, or marketing spend. If asked, say briefly that this is not in the data and suggest the closest question it can answer (for example food vs. wine revenue instead of best-selling dishes, or labour cost % instead of staff hours).

    Labour cost is allocated from the service level to visits. Questions such as "which service was overstaffed" are answerable through labour cost % per service, day or weekday, but not through the number of people on shift.
verified_queries:
  - name: '"How is each restaurant performing this year?"'
    question: How is each restaurant performing this year?
    sql: |-
      SELECT
        restaurant,
        ROUND(SUM(total_revenue)) AS revenue_dkk,
        SUM(guests) AS guests,
        ROUND(SUM(total_revenue) / NULLIF(SUM(guests), 0)) AS spend_per_guest_dkk,
        ROUND(100.0 * SUM(food_cost) / NULLIF(SUM(food_revenue), 0), 1) AS food_cost_pct,
        ROUND(100.0 * SUM(labour_cost) / NULLIF(SUM(total_revenue), 0), 1) AS labour_cost_pct,
        ROUND(100.0 * (SUM(food_cost) + SUM(beverage_cost) + SUM(labour_cost)) / NULLIF(SUM(total_revenue), 0), 1) AS prime_cost_pct
      FROM visits
      WHERE status = 'completed'
        AND visit_date >= '2026-01-01'
      GROUP BY restaurant
      ORDER BY revenue_dkk DESC;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: true
  - name: '"What is the revenue per month for each restaurant?"'
    question: What is the revenue per month for each restaurant?
    sql: |-
      SELECT
        DATE_TRUNC('month', visit_date) AS month,
        restaurant,
        ROUND(SUM(total_revenue)) AS revenue_dkk,
        SUM(guests) AS guests
      FROM visits
      WHERE status = 'completed'
      GROUP BY month, restaurant
      ORDER BY month, restaurant;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  - name: '"Which restaurant has the highest labour cost percentage, and how does it develop by month?"'
    question: Which restaurant has the highest labour cost percentage, and how does it develop by month?
    sql: |-
      SELECT
        DATE_TRUNC('month', visit_date) AS month,
        restaurant,
        ROUND(SUM(labour_cost)) AS labour_cost_dkk,
        ROUND(SUM(total_revenue)) AS revenue_dkk,
        ROUND(100.0 * SUM(labour_cost) / NULLIF(SUM(total_revenue), 0), 1) AS labour_cost_pct
      FROM visits
      WHERE status = 'completed'
      GROUP BY month, restaurant
      ORDER BY month, restaurant;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: true
  - name: '"Which weekdays are overstaffed at MARE?"'
    question: Which weekdays are overstaffed at MARE?
    sql: |-
      SELECT
        DAYNAME(visit_date) AS weekday,
        DAYOFWEEKISO(visit_date) AS weekday_number,
        COUNT(DISTINCT visit_date) AS open_days,
        ROUND(SUM(guests) / COUNT(DISTINCT visit_date)) AS guests_per_day,
        ROUND(100.0 * SUM(labour_cost) / NULLIF(SUM(total_revenue), 0), 1) AS labour_cost_pct
      FROM visits
      WHERE status = 'completed'
        AND restaurant = 'MARE'
      GROUP BY weekday, weekday_number
      ORDER BY weekday_number;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  - name: '"How has the food cost percentage developed by quarter for each restaurant?"'
    question: How has the food cost percentage developed by quarter for each restaurant?
    sql: |-
      SELECT
        DATE_TRUNC('quarter', visit_date) AS quarter,
        restaurant,
        ROUND(100.0 * SUM(food_cost) / NULLIF(SUM(food_revenue), 0), 1) AS food_cost_pct
      FROM visits
      WHERE status = 'completed'
      GROUP BY quarter, restaurant
      ORDER BY restaurant, quarter;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: true
  - name: '"What is the no-show rate by booking channel?"'
    question: What is the no-show rate by booking channel?
    sql: |-
      SELECT
        booking_channel,
        COUNT(*) AS bookings,
        COUNT_IF(status = 'no_show') AS no_shows,
        ROUND(100.0 * COUNT_IF(status = 'no_show') / NULLIF(COUNT(*), 0), 1) AS no_show_rate_pct,
        ROUND(100.0 * COUNT_IF(status = 'cancelled') / NULLIF(COUNT(*), 0), 1) AS cancellation_rate_pct
      FROM visits
      WHERE booking_channel <> 'walk_in'
      GROUP BY booking_channel
      ORDER BY no_show_rate_pct DESC;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: true
  - name: '"How does revenue this year compare with the same period last year?"'
    question: How does revenue this year compare with the same period last year?
    sql: |-
      WITH by_year AS (
        SELECT
          restaurant,
          SUM(CASE WHEN visit_date BETWEEN '2026-01-01' AND '2026-10-25' THEN total_revenue END) AS revenue_2026,
          SUM(CASE WHEN visit_date BETWEEN '2025-01-01' AND '2025-10-25' THEN total_revenue END) AS revenue_2025
        FROM visits
        WHERE status = 'completed'
        GROUP BY restaurant
      )
      SELECT
        restaurant,
        ROUND(revenue_2025) AS revenue_2025_jan_to_oct25_dkk,
        ROUND(revenue_2026) AS revenue_2026_jan_to_oct25_dkk,
        ROUND(100.0 * (revenue_2026 - revenue_2025) / NULLIF(revenue_2025, 0), 1) AS growth_pct
      FROM by_year
      ORDER BY growth_pct DESC;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  - name: '"What share of revenue is wine, and how much wine do we sell per guest?"'
    question: What share of revenue is wine, and how much wine do we sell per guest?
    sql: |-
      SELECT
        restaurant,
        ROUND(100.0 * SUM(wine_revenue) / NULLIF(SUM(total_revenue), 0), 1) AS wine_share_pct,
        ROUND(100.0 * (SUM(wine_revenue) + SUM(other_beverage_revenue)) / NULLIF(SUM(total_revenue), 0), 1) AS beverage_share_pct,
        ROUND(SUM(wine_revenue) / NULLIF(SUM(guests), 0)) AS wine_per_guest_dkk
      FROM visits
      WHERE status = 'completed'
      GROUP BY restaurant
      ORDER BY wine_per_guest_dkk DESC;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  - name: '"How far in advance do guests book?"'
    question: How far in advance do guests book?
    sql: |-
      SELECT
        occasion,
        COUNT(*) AS bookings,
        ROUND(AVG(DATEDIFF('minute', booked_at, TIMESTAMP_NTZ_FROM_PARTS(visit_date, visit_time)) / 1440.0), 1) AS avg_lead_time_days,
        ROUND(MEDIAN(DATEDIFF('minute', booked_at, TIMESTAMP_NTZ_FROM_PARTS(visit_date, visit_time)) / 1440.0), 1) AS median_lead_time_days
      FROM visits
      WHERE booking_channel <> 'walk_in'
      GROUP BY occasion
      ORDER BY median_lead_time_days DESC;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  - name: '"How many guests do we serve per day by service and weekday?"'
    question: How many guests do we serve per day by service and weekday?
    sql: |-
      SELECT
        restaurant,
        service,
        DAYNAME(visit_date) AS weekday,
        DAYOFWEEKISO(visit_date) AS weekday_number,
        ROUND(SUM(guests) / COUNT(DISTINCT visit_date)) AS guests_per_open_day
      FROM visits
      WHERE status = 'completed'
      GROUP BY restaurant, service, weekday, weekday_number
      ORDER BY restaurant, service, weekday_number;
    verified_at: 1793012400
    verified_by: AILO
    use_as_onboarding_question: false
  $$
);

-- The agent's role needs to read the view
GRANT SELECT ON SEMANTIC VIEW GENERAL_AGENT_DEMO.RESTAURANT.FORK_VISITS_SEMANTIC TO ROLE GENERAL_AGENT_ROLE;

-- Quick test: revenue and labour cost % per restaurant through the view
SELECT * FROM SEMANTIC_VIEW(
  GENERAL_AGENT_DEMO.RESTAURANT.FORK_VISITS_SEMANTIC
  DIMENSIONS VISITS.RESTAURANT
  METRICS VISITS.REVENUE, VISITS.LABOUR_COST_PCT
)
ORDER BY REVENUE DESC;

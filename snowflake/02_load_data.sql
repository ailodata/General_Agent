-- Load data/visits.csv into VISITS.
--
-- Easiest: in Snowsight, open GENERAL_AGENT_DEMO.RESTAURANT.VISITS -> Load Data,
-- pick the CSV, choose "skip header" and empty strings as NULL. Then run the checks at the bottom.
--
-- Or with SnowSQL / the Snowflake CLI, run the statements below from the repo root.

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE GENERAL_AGENT_WH;
USE SCHEMA GENERAL_AGENT_DEMO.RESTAURANT;

CREATE FILE FORMAT IF NOT EXISTS CSV_WITH_HEADER
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  EMPTY_FIELD_AS_NULL = TRUE
  NULL_IF = ('');

CREATE STAGE IF NOT EXISTS DEMO_STAGE FILE_FORMAT = CSV_WITH_HEADER;

PUT file://data/visits.csv @DEMO_STAGE AUTO_COMPRESS = TRUE OVERWRITE = TRUE;

TRUNCATE TABLE VISITS;
COPY INTO VISITS FROM @DEMO_STAGE/visits.csv.gz FILE_FORMAT = CSV_WITH_HEADER;

-- Checks: expect about 191k rows, 173k completed visits, 2 January 2025 to 25 October 2026
SELECT COUNT(*) AS rows_total,
       COUNT_IF(STATUS = 'completed') AS completed,
       COUNT(DISTINCT RESTAURANT) AS restaurants,
       SUM(TOTAL_REVENUE) AS revenue_dkk,
       MIN(VISIT_DATE) AS first_date,
       MAX(VISIT_DATE) AS last_date
FROM VISITS;

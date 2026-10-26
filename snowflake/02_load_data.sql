-- Load data/website_events.csv into WEBSITE_EVENTS.
--
-- Easiest: in Snowsight, open GENERAL_AGENT_DEMO.RESTAURANT.WEBSITE_EVENTS -> Load Data,
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

PUT file://data/website_events.csv @DEMO_STAGE AUTO_COMPRESS = TRUE OVERWRITE = TRUE;

TRUNCATE TABLE WEBSITE_EVENTS;
COPY INTO WEBSITE_EVENTS FROM @DEMO_STAGE/website_events.csv.gz FILE_FORMAT = CSV_WITH_HEADER;

-- Checks: expect about 96k rows, 3.3k conversions, 1 April to 18 October 2026
SELECT COUNT(*) AS rows_total,
       COUNT_IF(EVENT_TYPE = 'conversion') AS conversions,
       COUNT(DISTINCT VISITOR_ID) AS visitors,
       COUNT(DISTINCT SESSION_ID) AS sessions,
       MIN(EVENT_TIME) AS first_event,
       MAX(EVENT_TIME) AS last_event
FROM WEBSITE_EVENTS;

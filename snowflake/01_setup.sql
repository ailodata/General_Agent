-- FORK demo: database, schema, warehouse, role and table.
-- Run once as ACCOUNTADMIN (or a role that can create these objects) in a Snowsight worksheet.
-- Replace <YOUR_USER> with your Snowflake user name before running.

USE ROLE ACCOUNTADMIN;

-- Small warehouse that suspends quickly, so the demo costs as little as possible
CREATE WAREHOUSE IF NOT EXISTS GENERAL_AGENT_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- Monthly credit cap on the warehouse (adjust the quota as needed)
CREATE RESOURCE MONITOR IF NOT EXISTS GENERAL_AGENT_MONITOR
  WITH CREDIT_QUOTA = 10
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 80 PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND;
ALTER WAREHOUSE GENERAL_AGENT_WH SET RESOURCE_MONITOR = GENERAL_AGENT_MONITOR;

CREATE DATABASE IF NOT EXISTS GENERAL_AGENT_DEMO;
CREATE SCHEMA IF NOT EXISTS GENERAL_AGENT_DEMO.RESTAURANT;

-- Role used by the agent and the app. It only sees the demo schema.
CREATE ROLE IF NOT EXISTS GENERAL_AGENT_ROLE;
GRANT USAGE ON WAREHOUSE GENERAL_AGENT_WH TO ROLE GENERAL_AGENT_ROLE;
GRANT USAGE ON DATABASE GENERAL_AGENT_DEMO TO ROLE GENERAL_AGENT_ROLE;
GRANT USAGE ON SCHEMA GENERAL_AGENT_DEMO.RESTAURANT TO ROLE GENERAL_AGENT_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA GENERAL_AGENT_DEMO.RESTAURANT TO ROLE GENERAL_AGENT_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GENERAL_AGENT_DEMO.RESTAURANT TO ROLE GENERAL_AGENT_ROLE;
GRANT ROLE GENERAL_AGENT_ROLE TO USER <YOUR_USER>;

USE WAREHOUSE GENERAL_AGENT_WH;
USE SCHEMA GENERAL_AGENT_DEMO.RESTAURANT;

-- One row per table or party: a booking, a walk-in, a cancellation or a no-show. Amounts in DKK ex VAT.
CREATE OR REPLACE TABLE VISITS (
  VISIT_ID                VARCHAR   NOT NULL COMMENT 'Unique visit id',
  RESTAURANT              VARCHAR   NOT NULL COMMENT 'LIVO, VERDE, MORGEN, HAVEN, BISTRO 33, EMBER or MARE',
  CONCEPT                 VARCHAR   COMMENT 'Restaurant concept, e.g. Italian, Seafood',
  CITY                    VARCHAR   COMMENT 'City of the restaurant',
  VISIT_DATE              DATE      NOT NULL COMMENT 'Date of the visit (or of the booking that was cancelled or not shown)',
  VISIT_TIME              TIME      COMMENT 'Arrival time',
  SERVICE                 VARCHAR   COMMENT 'brunch, lunch or dinner',
  GUESTS                  NUMBER(3, 0) COMMENT 'Number of guests (covers)',
  STATUS                  VARCHAR   COMMENT 'completed, cancelled or no_show',
  BOOKING_CHANNEL         VARCHAR   COMMENT 'website, phone, booking_portal or walk_in',
  BOOKING_ID              VARCHAR   COMMENT 'Empty for walk-ins',
  BOOKED_AT               TIMESTAMP_NTZ COMMENT 'When the booking was made; empty for walk-ins',
  OCCASION                VARCHAR   COMMENT 'none, birthday, anniversary, business or group',
  FOOD_REVENUE            NUMBER(12, 2) COMMENT 'Food sales ex VAT; empty unless completed',
  WINE_REVENUE            NUMBER(12, 2) COMMENT 'Wine sales ex VAT',
  OTHER_BEVERAGE_REVENUE  NUMBER(12, 2) COMMENT 'Beer, drinks, soft drinks and coffee ex VAT',
  TOTAL_REVENUE           NUMBER(12, 2) COMMENT 'Food + wine + other beverages ex VAT',
  TIP                     NUMBER(12, 2) COMMENT 'Tip',
  PAYMENT_METHOD          VARCHAR   COMMENT 'card, mobile_pay, cash or invoice',
  FOOD_COST               NUMBER(12, 2) COMMENT 'Cost of goods for the food',
  BEVERAGE_COST           NUMBER(12, 2) COMMENT 'Cost of goods for wine and other beverages',
  LABOUR_COST             NUMBER(12, 2) COMMENT 'Labour cost of the service, allocated to completed visits by guests'
)
COMMENT = 'Synthetic visits for the fictional restaurant group FORK. No real data.';

GRANT SELECT ON TABLE VISITS TO ROLE GENERAL_AGENT_ROLE;

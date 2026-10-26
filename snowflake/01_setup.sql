-- Bistro Lind demo: database, schema, warehouse, role and table.
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

-- One row per event: a pageview or a conversion
CREATE OR REPLACE TABLE WEBSITE_EVENTS (
  EVENT_ID              VARCHAR   NOT NULL COMMENT 'Unique event id',
  EVENT_TIME            TIMESTAMP_NTZ NOT NULL COMMENT 'When the event happened',
  EVENT_TYPE            VARCHAR   NOT NULL COMMENT 'pageview or conversion',
  VISITOR_ID            VARCHAR   NOT NULL COMMENT 'Anonymous visitor id, stable across sessions',
  SESSION_ID            VARCHAR   NOT NULL COMMENT 'Session id',
  MARKET                VARCHAR   COMMENT 'English, Danish, Swedish or Norwegian site',
  LANGUAGE              VARCHAR   COMMENT 'Page language code; empty on the external booking widget',
  DEVICE_TYPE           VARCHAR   COMMENT 'mobile, desktop or tablet',
  VISIT_SOURCE          VARCHAR   COMMENT 'Channel: direct, organic, paid, social, email, referrals, ai-referrals',
  UTM_SOURCE            VARCHAR,
  UTM_MEDIUM            VARCHAR,
  UTM_CAMPAIGN          VARCHAR,
  REFERRER              VARCHAR,
  URL_DOMAIN            VARCHAR   COMMENT 'Main site or the external booking widget domain',
  URL_PATH              VARCHAR,
  PAGE_TITLE            VARCHAR,
  CONTENT_TYPE          VARCHAR   COMMENT 'STANDARD_PAGE, LANDING_PAGE, BLOG_POST or LISTING_PAGE',
  CONTENT_TOPIC         VARCHAR   COMMENT 'Topic of the page, e.g. menu_dinner, blog_recipes, gift_cards',
  FUNNEL_STAGE          VARCHAR   COMMENT 'top, mid, bottom or other',
  RESTAURANT_LOCATION   VARCHAR   COMMENT 'City of the restaurant page or of a table booking',
  CONVERSION_ID         VARCHAR   COMMENT 'Set on conversion events only',
  CONVERSION_TYPE       VARCHAR   COMMENT 'Table Booked, Gift Card Purchased, Loyalty Signup, Catering Enquiry, Newsletter Signup',
  CONVERSION_VALUE_EUR  NUMBER(10, 2) COMMENT 'Estimated value in EUR; 0 for signups',
  PARTY_SIZE            NUMBER(3, 0)  COMMENT 'Guests on a table booking'
)
COMMENT = 'Synthetic website events for the fictional restaurant chain Bistro Lind. No real data.';

GRANT SELECT ON TABLE WEBSITE_EVENTS TO ROLE GENERAL_AGENT_ROLE;

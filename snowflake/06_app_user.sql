-- Service user for the Streamlit app. It reuses the role FORK_COWORK_USER, which can only use the
-- FORK agent and read the data behind it.
-- Run as ACCOUNTADMIN. The token secret is shown ONCE in the output of the last statement:
-- copy it straight into the app's secrets (SNOWFLAKE_PAT) and nowhere else.

USE ROLE ACCOUNTADMIN;

-- 1. Service user (no password, cannot sign in to Snowsight)
CREATE USER IF NOT EXISTS FORK_APP_USER
  TYPE = SERVICE
  DEFAULT_ROLE = FORK_COWORK_USER
  DEFAULT_WAREHOUSE = GENERAL_AGENT_WH
  COMMENT = 'Streamlit app for the FORK demo agent';
GRANT ROLE FORK_COWORK_USER TO USER FORK_APP_USER;

-- 2. Streamlit Cloud has no fixed IP addresses, so the token cannot be tied to a network policy.
--    This lets the token work without one (any network policy that is set is still enforced).
CREATE AUTHENTICATION POLICY IF NOT EXISTS GENERAL_AGENT_DEMO.RESTAURANT.FORK_APP_PAT_POLICY
  PAT_POLICY = (NETWORK_POLICY_EVALUATION = ENFORCED_NOT_REQUIRED);
ALTER USER FORK_APP_USER SET AUTHENTICATION POLICY GENERAL_AGENT_DEMO.RESTAURANT.FORK_APP_PAT_POLICY;

-- 3. The token, limited to the role, valid for 365 days (the account maximum by default). Copy the token_secret from the output now.
ALTER USER FORK_APP_USER
  ADD PROGRAMMATIC ACCESS TOKEN FORK_APP_TOKEN
  ROLE_RESTRICTION = 'FORK_COWORK_USER'
  DAYS_TO_EXPIRY = 365
  COMMENT = 'Streamlit app for the FORK demo agent';

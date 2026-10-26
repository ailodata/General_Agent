-- Create the semantic view GENERAL_AGENT_DEMO.RESTAURANT.FORK_VISITS_SEMANTIC from agent/fork_visits_semantic.yaml.
-- Run as the role that owns the schema GENERAL_AGENT_DEMO.RESTAURANT.
--
-- Option A (Snowsight): AI & ML -> Cortex Analyst -> Create new -> Upload your YAML file,
--   pick GENERAL_AGENT_DEMO.RESTAURANT as location and upload agent/fork_visits_semantic.yaml.
--   Then run the GRANT at the bottom.
--
-- Option B (SQL): paste the whole content of agent/fork_visits_semantic.yaml between the $$ markers below.
--   Run it first with TRUE (validate only), then with FALSE (create).

USE WAREHOUSE GENERAL_AGENT_WH;

CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'GENERAL_AGENT_DEMO.RESTAURANT',
  $$
  -- paste agent/fork_visits_semantic.yaml here
  $$,
  TRUE  -- validate only; change to FALSE to create the view
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

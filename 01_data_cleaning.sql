-- ============================================================
-- PHASE 2: DATA CLEANING
-- SLA Breach & Root Cause Analyzer
-- ============================================================
-- Run these blocks in order. Each one is a discrete cleaning
-- step you can talk through separately in an interview.

USE cx_quality_project;

-- ------------------------------------------------------------
-- STEP 0: Baseline counts (run before AND after cleaning,
-- compare the numbers, that's your "before/after" proof)
-- ------------------------------------------------------------
SELECT COUNT(*) AS total_tickets FROM tickets;
SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority;
SELECT COUNT(*) AS missing_agent FROM tickets WHERE agent_id IS NULL;

-- ------------------------------------------------------------
-- STEP 1: Standardize categorical text
-- Fixes inconsistent casing in priority, and trims stray
-- whitespace in category (e.g. "  Billing Issue ")
-- ------------------------------------------------------------
UPDATE tickets
SET priority = CASE
    WHEN UPPER(TRIM(priority)) = 'CRITICAL' THEN 'Critical'
    WHEN UPPER(TRIM(priority)) = 'HIGH'     THEN 'High'
    WHEN UPPER(TRIM(priority)) = 'MEDIUM'   THEN 'Medium'
    WHEN UPPER(TRIM(priority)) = 'LOW'      THEN 'Low'
    ELSE TRIM(priority)
END;

UPDATE tickets
SET category = TRIM(category);

-- Sanity check: should now show exactly 4 clean priority values
SELECT priority, COUNT(*) FROM tickets GROUP BY priority;

-- ------------------------------------------------------------
-- STEP 2: Parse mixed date formats into real DATETIME columns
-- Two formats exist in the raw text: 'YYYY-MM-DD HH:MM:SS'
-- and 'DD/MM/YYYY HH:MM'. We detect which one a row uses by
-- checking for a '/' character, then parse accordingly.
-- ------------------------------------------------------------
ALTER TABLE tickets ADD COLUMN created_at_clean DATETIME;
ALTER TABLE tickets ADD COLUMN resolved_at_clean DATETIME;

UPDATE tickets
SET created_at_clean = CASE
    WHEN created_at LIKE '%/%' THEN STR_TO_DATE(created_at, '%d/%m/%Y %H:%i')
    ELSE STR_TO_DATE(created_at, '%Y-%m-%d %H:%i:%s')
END;

UPDATE tickets
SET resolved_at_clean = CASE
    WHEN resolved_at IS NULL OR resolved_at = '' THEN NULL
    WHEN resolved_at LIKE '%/%' THEN STR_TO_DATE(resolved_at, '%d/%m/%Y %H:%i')
    ELSE STR_TO_DATE(resolved_at, '%Y-%m-%d %H:%i:%s')
END;

-- ------------------------------------------------------------
-- STEP 3: Flag logical impossibilities (resolved before created)
-- We FLAG these rather than deleting or "fixing" them, because
-- we have no way to know the true resolution time. Flagging
-- preserves the raw record while excluding it from time-based
-- calculations later. This is a judgment call worth explaining
-- in an interview: never silently fabricate a corrected value.
-- ------------------------------------------------------------
ALTER TABLE tickets ADD COLUMN is_logic_error TINYINT(1) DEFAULT 0;

UPDATE tickets
SET is_logic_error = 1
WHERE resolved_at_clean IS NOT NULL
  AND resolved_at_clean < created_at_clean;

SELECT COUNT(*) AS logic_errors FROM tickets WHERE is_logic_error = 1;

-- ------------------------------------------------------------
-- STEP 4: Identify and remove near-duplicate tickets
-- Same category, sub_category, priority, channel, agent,
-- segment, and timestamps = almost certainly the same
-- underlying complaint logged twice under a different ID.
-- We keep the lowest ticket_id and drop the rest.
-- ------------------------------------------------------------

-- First, just look at what would be flagged (always inspect before deleting)
SELECT ticket_id, rn FROM (
    SELECT ticket_id,
           ROW_NUMBER() OVER (
               PARTITION BY category, sub_category, priority, channel,
                            agent_id, customer_segment, created_at, resolved_at
               ORDER BY ticket_id
           ) AS rn
    FROM tickets
) ranked
WHERE rn > 1;

-- Once you've confirmed these look like genuine duplicates, delete them
DELETE t FROM tickets t
JOIN (
    SELECT ticket_id,
           ROW_NUMBER() OVER (
               PARTITION BY category, sub_category, priority, channel,
                            agent_id, customer_segment, created_at, resolved_at
               ORDER BY ticket_id
           ) AS rn
    FROM tickets
) ranked ON t.ticket_id = ranked.ticket_id
WHERE ranked.rn > 1;

-- ------------------------------------------------------------
-- STEP 5: Derive resolution time and SLA breach flag
-- Excludes still-open tickets (resolved_at_clean IS NULL)
-- and logic-error rows from the calculation entirely.
-- ------------------------------------------------------------
ALTER TABLE tickets ADD COLUMN resolution_hours DECIMAL(10,2);
ALTER TABLE tickets ADD COLUMN sla_breached TINYINT(1);

UPDATE tickets
SET resolution_hours = TIMESTAMPDIFF(MINUTE, created_at_clean, resolved_at_clean) / 60.0
WHERE resolved_at_clean IS NOT NULL AND is_logic_error = 0;

UPDATE tickets
SET sla_breached = CASE WHEN resolution_hours > sla_target_hours THEN 1 ELSE 0 END
WHERE resolution_hours IS NOT NULL;

-- ------------------------------------------------------------
-- STEP 6: Final verification
-- Compare these counts back against Step 0's baseline numbers
-- ------------------------------------------------------------
SELECT COUNT(*) AS total_tickets_after_cleaning FROM tickets;
SELECT COUNT(*) AS tickets_ready_for_analysis FROM tickets WHERE sla_breached IS NOT NULL;

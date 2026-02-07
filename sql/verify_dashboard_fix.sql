-- SQL Queries to Verify Dashboard Time Filtering Fix
-- Run these to manually verify the fix is working

-- Set time range (adjust as needed)
-- For "7 days": NOW() - INTERVAL '7 days'
-- For "30 days": NOW() - INTERVAL '30 days'
-- For "Today": CURRENT_DATE

\set start_time 'NOW() - INTERVAL ''7 days'''

-- ==========================================
-- Test 1: SessionAnalysisLog time filtering
-- ==========================================

SELECT
    'Total SessionAnalysisLog records' AS description,
    COUNT(*) AS count
FROM session_analysis_log;

SELECT
    'SessionAnalysisLog within time range' AS description,
    COUNT(*) AS count
FROM session_analysis_log
WHERE analyzed_at >= :start_time;

SELECT
    'SessionAnalysisLog OUTSIDE time range (should NOT be counted)' AS description,
    COUNT(*) AS count
FROM session_analysis_log
WHERE analyzed_at < :start_time;

-- ==========================================
-- Test 2: Cost Comparison (Before vs After)
-- ==========================================

-- BEFORE FIX (ALL TIME - WRONG)
SELECT
    'BEFORE FIX: All-time Gemini cost' AS description,
    COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd
FROM session_analysis_log;

-- AFTER FIX (TIME FILTERED - CORRECT)
SELECT
    'AFTER FIX: Time-filtered Gemini cost' AS description,
    COALESCE(SUM(estimated_cost_usd), 0) AS total_cost_usd
FROM session_analysis_log
WHERE analyzed_at >= :start_time;

-- ==========================================
-- Test 3: Top Users Query (Simulated)
-- ==========================================

-- BEFORE FIX (Missing SessionAnalysisLog.analyzed_at filter)
SELECT
    c.email,
    COUNT(DISTINCT su.session_id) AS total_sessions,
    COALESCE(SUM(su.duration_seconds * 0.40 / 3600.0), 0) +
    COALESCE(SUM(sal.estimated_cost_usd), 0) AS total_cost_usd
FROM session_usage su
JOIN counselors c ON su.counselor_id = c.id
LEFT JOIN session_analysis_log sal ON su.session_id = sal.session_id
WHERE su.created_at >= :start_time  -- ✅ Filters usage
  -- ❌ MISSING: AND (sal.id IS NULL OR sal.analyzed_at >= :start_time)
GROUP BY c.email
ORDER BY total_cost_usd DESC
LIMIT 5;

-- AFTER FIX (Correct filter)
SELECT
    c.email,
    COUNT(DISTINCT su.session_id) AS total_sessions,
    COALESCE(SUM(su.duration_seconds * 0.40 / 3600.0), 0) +
    COALESCE(SUM(sal.estimated_cost_usd), 0) AS total_cost_usd
FROM session_usage su
JOIN counselors c ON su.counselor_id = c.id
LEFT JOIN session_analysis_log sal ON su.session_id = sal.session_id
WHERE su.created_at >= :start_time  -- ✅ Filters usage
  AND (sal.id IS NULL OR sal.analyzed_at >= :start_time)  -- ✅ Filters analysis
GROUP BY c.email
ORDER BY total_cost_usd DESC
LIMIT 5;

-- ==========================================
-- Test 4: User Segments (Activity Check)
-- ==========================================

-- Count users by activity time range
SELECT
    CASE
        WHEN MAX(su.created_at) IS NULL THEN 'No activity'
        WHEN MAX(su.created_at) >= NOW() - INTERVAL '7 days' THEN 'Active (< 7 days)'
        WHEN MAX(su.created_at) >= NOW() - INTERVAL '30 days' THEN 'At-Risk (7-30 days)'
        ELSE 'Churned (> 30 days)'
    END AS segment,
    COUNT(*) AS user_count
FROM counselors c
LEFT JOIN session_usage su ON c.id = su.counselor_id
WHERE c.created_at < NOW() - INTERVAL '7 days'  -- Only users older than 7 days
GROUP BY segment;

-- ==========================================
-- Test 5: Cost Distribution by Date
-- ==========================================

-- Show daily Gemini costs for last 7 days
SELECT
    DATE(analyzed_at) AS date,
    COUNT(*) AS analysis_count,
    COALESCE(SUM(estimated_cost_usd), 0) AS daily_gemini_cost
FROM session_analysis_log
WHERE analyzed_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(analyzed_at)
ORDER BY date DESC;

-- ==========================================
-- Test 6: Verify outerjoin NULL handling
-- ==========================================

-- Sessions without analysis logs (should still be counted)
SELECT
    'Sessions with analysis logs' AS category,
    COUNT(*) AS count
FROM session_usage su
INNER JOIN session_analysis_log sal ON su.session_id = sal.session_id
WHERE su.created_at >= :start_time;

SELECT
    'Sessions without analysis logs' AS category,
    COUNT(*) AS count
FROM session_usage su
LEFT JOIN session_analysis_log sal ON su.session_id = sal.session_id
WHERE su.created_at >= :start_time
  AND sal.id IS NULL;

-- Total (should equal sum of above)
SELECT
    'Total sessions in time range' AS category,
    COUNT(*) AS count
FROM session_usage
WHERE created_at >= :start_time;

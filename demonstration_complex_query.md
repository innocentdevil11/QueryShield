# QueryShield vs Baseline: Complex Query Demonstration

This document captures a real-world demonstration of the **QueryShield Cognitive Pipeline** versus a standard **Direct-Prompt Baseline** using SambaNova's `Meta-Llama-3.3-70B-Instruct` model on the highly relational `IPL` database.

## The Challenge

**Database:** `IPL`
**Prompt:**
> *"List the names of all players who have taken at least 5 wickets in a single match, but who also have a career batting strike rate of less than 100. Order the final list by their total number of career wickets taken across all seasons, from highest to lowest."*

This query is exceptionally difficult because:
1. It requires multi-level aggregations (grouping by `match_id` for the 5-wicket haul, and by `player` for career stats).
2. It requires complex math (strike rate calculation).
3. It requires joining multiple heavy tables (`wicket_taken`, `ball_by_ball`, `batsman_scored`, `player`).

---

## ❌ The Baseline Output (Direct Prompting)

```sql
SELECT p.player_name
FROM player p
WHERE p.player_id IN (
  SELECT wt.player_out
  FROM wicket_taken wt
  GROUP BY wt.player_out
  HAVING COUNT(wt.player_out) >= 5
)
AND p.player_id IN (
  SELECT bbb.striker
  FROM ball_by_ball bbb
  JOIN batsman_scored bs ON bbb.match_id = bs.match_id AND bbb.over_id = bs.over_id AND bbb.ball_id = bs.ball_id AND bbb.innings_no = bs.innings_no
  GROUP BY bbb.striker
  HAVING SUM(bs.runs_scored) * 1.0 / COUNT(bbb.ball_id) < 100
)
ORDER BY (
  SELECT COUNT(wt2.ball_id)
  FROM wicket_taken wt2
  WHERE wt2.player_out = p.player_id
) DESC;
```

### Why it Failed:
1. **The "Wicket Taker" Trap:** The Baseline queried `SELECT wt.player_out FROM wicket_taken`. However, `player_out` is the batsman who was dismissed! It hallucinated that the player getting out was the bowler.
2. **The "Single Match" Trap:** The Baseline ignored the requirement for the wickets to be *"in a single match"*. It just grouped by `wt.player_out` across their entire career.
3. **Messy Architecture:** It attempted to write the entire query using deeply nested `IN (SELECT...)` clauses, causing cognitive overload for the model.

---

## 🏆 The QueryShield Output (Cognitive Pipeline)

```sql
WITH wickets AS (
  SELECT 
    bbb.bowler AS player_id,
    wt.match_id,
    COUNT(wt.player_out) AS wickets
  FROM 
    wicket_taken wt
  INNER JOIN 
    ball_by_ball bbb 
    ON wt.match_id = bbb.match_id 
    AND wt.over_id = bbb.over_id 
    AND wt.ball_id = bbb.ball_id 
    AND wt.innings_no = bbb.innings_no
  GROUP BY 
    bbb.bowler, 
    wt.match_id
  HAVING 
    COUNT(wt.player_out) >= 5
),
batting_stats AS (
  SELECT 
    bbb.striker AS player_id,
    SUM(bs.runs_scored) * 1.0 / COUNT(bs.ball_id) AS batting_strike_rate
  FROM 
    ball_by_ball bbb
  INNER JOIN 
    batsman_scored bs 
    ON bbb.match_id = bs.match_id 
    AND bbb.over_id = bs.over_id 
    AND bbb.ball_id = bs.ball_id 
    AND bbb.innings_no = bs.innings_no
  GROUP BY 
    bbb.striker
),
career_wickets AS (
  SELECT 
    bbb.bowler AS player_id,
    COUNT(wt.player_out) AS total_wickets
  FROM 
    wicket_taken wt
  INNER JOIN 
    ball_by_ball bbb 
    ON wt.match_id = bbb.match_id 
    AND wt.over_id = bbb.over_id 
    AND wt.ball_id = bbb.ball_id 
    AND wt.innings_no = bbb.innings_no
  GROUP BY 
    bbb.bowler
)
SELECT 
  p.player_name
FROM 
  player p
INNER JOIN 
  wickets w 
  ON p.player_id = w.player_id
INNER JOIN 
  batting_stats bs 
  ON p.player_id = bs.player_id
INNER JOIN 
  career_wickets cw 
  ON p.player_id = cw.player_id
WHERE 
  bs.batting_strike_rate < 100
ORDER BY 
  cw.total_wickets DESC;
```

### Why it Succeeded:
1. **Schema Pruning (Semantic Filtering):** The massive IPL schema was silently pruned down to only the relevant tables (`player`, `ball_by_ball`, `wicket_taken`, `batsman_scored`).
2. **Planner-Enforced Logic:** The System generated a JSON plan first, breaking the problem down into isolated steps.
3. **Flawless Execution:**
   - It correctly joined `wicket_taken` to `ball_by_ball` to identify the actual bowler (`bbb.bowler`).
   - It properly grouped by both `bbb.bowler` and `wt.match_id` to isolate 5-wicket hauls within a single match.
   - It isolated the operations into clean `WITH ... AS (...)` Common Table Expressions (CTEs), culminating in a simple, highly readable final `JOIN`.

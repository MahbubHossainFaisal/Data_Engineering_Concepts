select player_name, scoring_class, is_active from players where current_season = 2022;


-- DROP TABLE players_scd;
-- CREATE TABLE players_scd (
-- 	player_name text,
-- 	scoring_class scoring_class,
-- 	is_active boolean,
-- 	start_season integer,
-- 	end_season integer,
-- 	current_season integer,
-- 	PRIMARY KEY(player_name,start_season)
-- );

INSERT INTO PLAYERS_SCD
with previous AS(
SELECT player_name,
	   current_season,
	   scoring_class,
	   is_active,
	   lag(scoring_class) OVER (PARTITION BY player_name ORDER BY current_season) as previous_scoring_class,
	   lag(is_active) OVER (PARTITION BY player_name ORDER BY current_season) as previous_is_active
FROM players
WHERE CURRENT_SEASON <= 2021)
,

indicators as (
SELECT *, CASE
			WHEN scoring_class <> previous_scoring_class THEN 1 
			WHEN is_active <> previous_is_active THEN 1
			ELSE 0 
		  END AS change_indicator
		  
FROM previous),

streaks as(
SELECT *, SUM(change_indicator) 
			OVER(PARTITION BY player_name ORDER BY current_season)
			AS streak_identifier
FROM indicators
)

SELECT player_name,
	   scoring_class,
	   is_active,
	   MIN(current_season) AS start_season,
	   MAX(current_season) AS end_season,
	   2021 as CURRENT_SEASON
FROM streaks
GROUP BY player_name,streak_identifier,is_active,scoring_class
ORDER BY player_name;

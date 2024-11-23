-- SELECT * FROM PLAYER_SEASONS;

-- create type season_stats AS (
-- 	season INTEGER,
-- 	gp INTEGER,
-- 	pts real,
-- 	reb real,
-- 	ast real
-- );

DROP TABLE players;
CREATE TABLE players(
player_name TEXT,
height text,
college text,
country text,
draft_year text,
draft_round text,
draft_number text,
season_stats season_stats[],
current_season INTEGER,
PRIMARY KEY(player_name,current_season)
)


INSERT INTO PLAYERS
with yesterday as(
select * from players where current_season = 2000
),
	today as (
select * from player_seasons where season = 2001
	)

select
	coalesce(t.player_name,y.player_name) as player_name,
	coalesce(t.height,y.height) as height,
	coalesce(t.college,y.college) as college,
	coalesce(t.country,y.country) as country,
	coalesce(t.draft_year,y.draft_year) as draft_year,
	coalesce(t.draft_round,y.draft_round) as draft_round,
	coalesce(t.draft_number,y.draft_number) as draft_number,
	case when y.season_stats is NULL 
		THEN ARRAY[ROW(
			t.season,
			t.gp,
			t.pts,
			t.reb,
			t.ast
		)::season_stats]
		WHEN t.season is not NULL THEN y.season_stats || ARRAY[ROW(
			t.season,
			t.gp,
			t.pts,
			t.reb,
			t.ast
		)::season_stats]
		ELSE y.season_stats
	END as season_stats,
	coalesce(t.season,y.current_season+1) as current_season


from today t FULL OUTER JOIN yesterday y 
	on y.player_name = t.player_name;


select * from players;


select max(season) from player_seasons;
select * from player_seasons where player_name ='Lionel Simmons';

select distinct current_season from players order by current_season;

select * from players where current_season = 2001 and player_name='Michael Jordan';





-- Unnesting the season stats

with unnested as(
select player_name, unnest(season_stats) as season_stats
from players where current_season = 2001 
)
select player_name,(season_stats::season_stats).* from unnested;



-- new type addition

create type scoring_class as ENUM('star','good','average','bad');


DROP TABLE players;
CREATE TABLE players(
player_name TEXT,
height text,
college text,
country text,
draft_year text,
draft_round text,
draft_number text,
season_stats season_stats[],
scoring_class scoring_class,
years_since_last_season integer,
current_season INTEGER,
PRIMARY KEY(player_name,current_season)
);



INSERT INTO PLAYERS
with yesterday as(
select * from players where current_season = 2000
),
	today as (
select * from player_seasons where season = 2001
	)

select
	coalesce(t.player_name,y.player_name) as player_name,
	coalesce(t.height,y.height) as height,
	coalesce(t.college,y.college) as college,
	coalesce(t.country,y.country) as country,
	coalesce(t.draft_year,y.draft_year) as draft_year,
	coalesce(t.draft_round,y.draft_round) as draft_round,
	coalesce(t.draft_number,y.draft_number) as draft_number,
	case when y.season_stats is NULL 
		THEN ARRAY[ROW(
			t.season,
			t.gp,
			t.pts,
			t.reb,
			t.ast
		)::season_stats]
		WHEN t.season is not NULL THEN y.season_stats || ARRAY[ROW(
			t.season,
			t.gp,
			t.pts,
			t.reb,
			t.ast
		)::season_stats]
		ELSE y.season_stats
	END as season_stats,

	case when t.season is not null then
		case when t.pts > 20 then 'star'
			 when t.pts > 15 then 'good'
			 when t.pts > 10 then 'average'
			 Else 'bad'
		end::scoring_class
		ELSE y.scoring_class
	end as scoring_class,

	case when t.season is not null then 0
	else y.years_since_last_season + 1
	END as years_since_last_season,
	coalesce(t.season,y.current_season+1) as current_season


from today t FULL OUTER JOIN yesterday y 
	on y.player_name = t.player_name;


select * from players where current_season=2001;



-- Who is the most improved player!

select 
player_name,
(season_stats[1]::season_stats).pts /
CASE WHEN (season_stats[cardinality(season_stats)]::season_stats).pts = 0 THEN 1 
ELSE  (season_stats[cardinality(season_stats)]::season_stats).pts END AS Player_Improvement

from players where current_season = 2001
ORDER BY 2 DESC;
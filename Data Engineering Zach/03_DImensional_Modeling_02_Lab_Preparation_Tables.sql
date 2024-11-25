INSERT INTO players
with years as
(
select * from generate_series(1996,2022) as season
)
--select * from years;
,
p as
(
select player_name, MIN(season) as first_season
from player_seasons
group by player_name
)
--select * from p;
,
players_and_seasons as
(
select * from
p join years y
on p.first_season <= y.season
)
--select * from players_and_seasons order by player_name
,
--select * from player_seasons where season is null;
windowed as
(SELECT
ps.player_name,ps.season,
array_remove(
        array_agg(case 
            when p1.season is not null then 
                cast(row(p1.season, p1.gp, p1.pts, p1.reb, p1.ast) as season_stats)
            end
        ) over (partition by ps.player_name order by coalesce(p1.season, ps.season)), 
        null
    ) as seasons
		from players_and_seasons ps
		left join player_seasons p1
		on ps.player_name = p1.player_name and ps.season = p1.season
		order by ps.player_name,ps.season
)
--SELECT * FROM windowed
,
static as (
select player_name,
       max(height) as height,
       max(college) as college,
       max(country) as country,
       max(draft_year) as draft_year,
       max(draft_round) as draft_round,
       max(draft_number) as draft_number
from player_seasons ps 
group by player_name
)

select 
	w.player_name, 
	s.height,
	s.college,
	s.country,
	s.draft_year,
	s.draft_number,
	s.draft_round,
	seasons as season_stats
--	,( seasons[cardinality(seasons)]).pts
	,case 
	when (seasons[cardinality(seasons)]).pts > 20 then 'star'
	when (seasons[cardinality(seasons)]).pts > 15 then 'good'
	when (seasons[cardinality(seasons)]).pts > 10 then 'average'
	else 'bad'
	end :: scoring_class as scorring_class
	,w.season - (seasons[cardinality(seasons)]).season as years_since_last_season
	,w.season as current_season
	,(seasons[cardinality(seasons)]).season = w.season as is_active
from windowed w 
join static s
on w.player_name = s.player_name;
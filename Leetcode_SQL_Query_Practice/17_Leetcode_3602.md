We have two tables
    1) Drivers
        - driver_id
        - driver_name
    2) Trip
        - Trip_id
        - driver_id
        - trip_date
        - distance
        - fuel_consumption

    CTE1 -> Everything from Trip, distance/fuel_consumption as fuel_efficiency

    CTE2 -> driver_id, driver_name, case when month(trip_date) between 1 and 6 then round(avg(fuel_consumption),2) ELSE NULL as first_half_avg,
    case when month(trip_date) between 7 to 12 then round(avg(fuel_consumption),2) ELSE NULL as second_half_avg,
    ROUND(second_half_avg-first_half_avg,2) as improved_efficiency
    FROM CTE1
    LEFT JOIN
    Drivers
    on CTE1.driver_id = Drivers.driver_id
    WHERE second_half_avg > first_half_avg
    ORDER By Improved_efficiency DESC, driver_name ASC


WITH CTE1 AS (
    SELECT 
        *,
        distance / fuel_consumption AS fuel_efficiency
    FROM 
        Trip
),
CTE2 AS (
    SELECT 
        c.driver_id, 
        driver_name,
        CASE WHEN EXTRACT(MONTH FROM trip_date) BETWEEN 1 AND 6 
             THEN ROUND(AVG(fuel_efficiency), 2) 
             ELSE NULL END AS first_half_avg,
        CASE WHEN EXTRACT(MONTH FROM trip_date) BETWEEN 7 AND 12 
             THEN ROUND(AVG(fuel_efficiency), 2) 
             ELSE NULL END AS second_half_avg
        from cte c
        left_join driver d
        on c.driver_id = d.driver_id
        group by c.driver_id, driver_name
)

Select *, second_half_avg-first_half_avg as efficiency_improvement

FROM CTE2 
where second_half_avg > first_half_avg
ORDER BY
efficiency_improvement DESC, driver_name;
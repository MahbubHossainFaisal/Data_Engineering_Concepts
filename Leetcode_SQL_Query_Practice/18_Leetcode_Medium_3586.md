with first_positive as
(
    select patient_id, min(test_date) as first_positive_date
    from covid_tests
    where result = 'Positive'
    group by patient_id
),
 first_negative as 
(
    select c.patient_id, min(c.test_date) as c.first_negative_date
    from covid_tests c
    inner join first_positive fp
    on 
    c.patient_id = fp.patient_id
    Where 
    fp.first_positive_date < c.first_negative_date
    and c.result = 'Negative'
    group by c.patient_id
)

SELECT 
  p.patient_id,
  p.patient_name,
  p.age,
  DATEDIFF(day, fp.first_positive_test, fn.first_negative_test) AS recovery_time
FROM first_positive fp
JOIN first_negative fn ON fp.patient_id = fn.patient_id
JOIN patients p ON p.patient_id = fp.patient_id
ORDER BY recovery_time, p.patient_name;
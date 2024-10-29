-- выбор пользователей которые сформировали первый отчёт в 2021 году
-- и сумма вознаграждения за 2022 год для каждого такого пользователя
SELECT user_id, sum(reward)
FROM reports
WHERE '2022-01-01' <= created_at
  AND created_at < '2023-01-01'
  AND user_id IN (SELECT user_id
                  from reports
                  GROUP BY user_id
                  HAVING '2021-01-01' <= min(created_at)
                     AND min(created_at) < '2022-01-01')
GROUP BY user_id;
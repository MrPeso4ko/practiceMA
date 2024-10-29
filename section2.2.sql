SELECT title, array_agg((barcode, price)) reports
FROM reports
         JOIN pos ON reports.pos_id = pos.id
GROUP BY title;
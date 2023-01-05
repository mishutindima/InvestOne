/* KILL ALL EXISTING CONNECTION FROM ORIGINAL DB (sourcedb)*/
SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity 
WHERE pg_stat_activity.datname = 'investonedb' AND pid <> pg_backend_pid();

/* CLONE DATABASE TO NEW ONE(TARGET_DB) */
CREATE DATABASE test_investonedb WITH TEMPLATE investonedb OWNER postgres;


select *
from "History_moneydeal" hm2  
where extract (year from hm2.datetime) = 2021


select * 
from "History_repodeal" hh  

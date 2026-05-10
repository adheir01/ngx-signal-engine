-- stg_global_prices.sql

select
    ticker,
    trade_date,
    close_price::float   as close_price,
    volume,
    market,
    ingested_at
from {{ source('public', 'global_prices') }}
where close_price is not null

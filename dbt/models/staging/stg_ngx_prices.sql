-- stg_ngx_prices.sql
-- Clean and type-cast raw NGX price data

select
    ticker,
    trade_date,
    open_price::float      as open_price,
    high_price::float      as high_price,
    low_price::float       as low_price,
    close_price::float     as close_price,
    coalesce(volume, 0)    as volume,
    market,
    ingested_at
from {{ source('public', 'ngx_prices') }}
where close_price is not null

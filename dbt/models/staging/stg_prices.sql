-- stg_prices.sql
-- Unified staging model — NGX and global prices in one place.
-- This is the single source of truth for all downstream models.

select
    ticker,
    trade_date,
    open_price::float       as open_price,
    high_price::float       as high_price,
    low_price::float        as low_price,
    close_price::float      as close_price,
    coalesce(volume, 0)     as volume,
    market
from {{ source('public', 'ngx_prices') }}
where close_price is not null

union all

select
    ticker,
    trade_date,
    open_price::float       as open_price,
    high_price::float       as high_price,
    low_price::float        as low_price,
    close_price::float      as close_price,
    coalesce(volume, 0)     as volume,
    market
from {{ source('public', 'global_prices') }}
where close_price is not null
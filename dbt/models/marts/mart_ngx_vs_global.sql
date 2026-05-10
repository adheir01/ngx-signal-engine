-- mart_ngx_vs_global.sql
-- Compare NGX vs EU/US market behaviour:
-- volatility, avg daily return, volume consistency

with ngx as (
    select
        trade_date,
        avg(close_price)                                    as avg_close,
        stddev(close_price)                                 as price_stddev,
        avg(volume)                                         as avg_volume
    from {{ ref('stg_ngx_prices') }}
    group by trade_date
),

global as (
    select
        market,
        trade_date,
        avg(close_price)                                    as avg_close,
        stddev(close_price)                                 as price_stddev,
        avg(volume)                                         as avg_volume
    from {{ ref('stg_global_prices') }}
    group by market, trade_date
),

ngx_labeled as (
    select 'NGX' as market, trade_date, avg_close, price_stddev, avg_volume
    from ngx
)

select * from ngx_labeled
union all
select market, trade_date, avg_close, price_stddev, avg_volume from global
order by market, trade_date

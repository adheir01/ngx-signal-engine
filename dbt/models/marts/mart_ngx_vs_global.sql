with ngx_returns as (
    select
        n.ticker,
        n.trade_date,
        n.close_price,
        n.volume,
        (n.close_price / nullif(lag(n.close_price) over (
            partition by n.ticker order by n.trade_date
        ), 0) - 1) * 100 as daily_return
    from {{ ref('stg_ngx_prices') }} n
),

global_returns as (
    select
        g.ticker,
        g.market,
        g.trade_date,
        g.close_price,
        g.volume,
        (g.close_price / nullif(lag(g.close_price) over (
            partition by g.ticker, g.market order by g.trade_date
        ), 0) - 1) * 100 as daily_return
    from {{ ref('stg_global_prices') }} g
),

ngx as (
    select
        'NGX'                       as market,
        trade_date,
        avg(close_price)            as avg_close,
        stddev(daily_return)        as price_stddev,
        avg(volume)                 as avg_volume
    from ngx_returns
    group by trade_date
),

global as (
    select
        market,
        trade_date,
        avg(close_price)            as avg_close,
        stddev(daily_return)        as price_stddev,
        avg(volume)                 as avg_volume
    from global_returns
    group by market, trade_date
)

select * from ngx
union all
select * from global
order by market, trade_date
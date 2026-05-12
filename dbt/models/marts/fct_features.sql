-- fct_features.sql
-- Master feature table. One row per ticker per date.
-- This is what the Python scoring layer reads from.

with returns as (
    select * from {{ ref('int_returns') }}
),

moving_avgs as (
    select * from {{ ref('int_moving_averages') }}
),

joined as (
    select
        r.ticker,
        r.trade_date,
        r.market,
        r.close_price,
        r.return_1d,
        r.return_5d,
        r.momentum_5d,
        m.sma_10,
        m.sma_20,
        m.ema_10,
        m.volume_ratio,

        -- SMA crossover flag
        case
            when m.sma_10 > m.sma_20 then 'bullish'
            when m.sma_10 < m.sma_20 then 'bearish'
            else 'neutral'
        end as sma_trend,

        -- Volume spike flag
        case when m.volume_ratio > 1.5 then true else false end as volume_spike,

        -- Price above both MAs
        case
            when r.close_price > m.sma_10
            and r.close_price > m.sma_20 then true
            else false
        end as price_above_mas

    from returns r
    join moving_avgs m
        on r.ticker = m.ticker
        and r.trade_date = m.trade_date
)

select * from joined
order by ticker, trade_date
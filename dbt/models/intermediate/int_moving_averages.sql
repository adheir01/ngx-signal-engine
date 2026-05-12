-- int_moving_averages.sql
-- Moving averages and volume ratios per ticker.

select
    ticker,
    trade_date,
    market,
    close_price,
    volume,

    -- Simple moving averages
    round(avg(close_price) over (
        partition by ticker order by trade_date
        rows between 9 preceding and current row
    )::numeric, 4) as sma_10,

    round(avg(close_price) over (
        partition by ticker order by trade_date
        rows between 19 preceding and current row
    )::numeric, 4) as sma_20,

    -- Exponential moving average (approximated in SQL)
    round(avg(close_price) over (
        partition by ticker order by trade_date
        rows between 9 preceding and current row
    )::numeric, 4) as ema_10,

    -- Volume ratio vs 10-day average
    round(
        volume::numeric / nullif(
            avg(volume) over (
                partition by ticker order by trade_date
                rows between 9 preceding and current row
            ), 0
        ), 4
    ) as volume_ratio,

    -- RSI components
    close_price - lag(close_price) over (
        partition by ticker order by trade_date
    ) as price_delta

from {{ ref('stg_prices') }}
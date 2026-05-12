-- int_returns.sql
-- Daily and multi-day returns per ticker.

select
    ticker,
    trade_date,
    market,
    close_price,
    volume,

    -- 1-day return
    round(
        (close_price / nullif(
            lag(close_price) over (partition by ticker order by trade_date), 0
        ) - 1)::numeric * 100, 4
    ) as return_1d,

    -- 5-day momentum
    round(
        (close_price - lag(close_price, 5) over (
            partition by ticker order by trade_date
        ))::numeric, 4
    ) as momentum_5d,

    -- 5-day return %
    round(
        (close_price / nullif(
            lag(close_price, 5) over (partition by ticker order by trade_date), 0
        ) - 1)::numeric * 100, 4
    ) as return_5d

from {{ ref('stg_prices') }}
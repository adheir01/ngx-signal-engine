-- mart_signal_performance.sql
-- How well did each signal type perform per ticker?
-- Uses backtest_trades to measure actual outcome rates.

with signal_outcomes as (
    select
        bt.ticker,
        bt.signal_at_entry,
        bt.outcome,
        bt.return_pct,
        br.win_rate,
        br.avg_return_pct,
        br.max_drawdown,
        br.sharpe_ratio,
        br.total_trades
    from {{ source('public', 'backtest_trades') }} bt
    join {{ source('public', 'backtest_runs') }} br
        on bt.run_id = br.id
)

select
    ticker,
    signal_at_entry                                    as signal_type,
    count(*)                                           as total_signals,
    round(avg(return_pct)::numeric, 4)                 as avg_return_pct,
    round(sum(case when outcome = 'WIN' then 1 else 0 end)::numeric
          / nullif(count(*), 0), 4)                    as win_rate,
    round(min(return_pct)::numeric, 4)                 as worst_trade,
    round(max(return_pct)::numeric, 4)                 as best_trade,
    max(sharpe_ratio)                                  as sharpe_ratio,
    max(max_drawdown)                                  as max_drawdown
from signal_outcomes
group by ticker, signal_at_entry
order by avg_return_pct desc

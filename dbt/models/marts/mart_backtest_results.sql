-- mart_backtest_results.sql
-- Summary of latest backtest run per ticker

select distinct on (ticker)
    ticker,
    run_name,
    start_date,
    end_date,
    total_trades,
    round(win_rate::numeric * 100, 2)       as win_rate_pct,
    round(avg_return_pct::numeric, 4)       as avg_return_pct,
    round(max_drawdown::numeric, 4)         as max_drawdown,
    round(sharpe_ratio::numeric, 4)         as sharpe_ratio,
    run_at
from {{ source('public', 'backtest_runs') }}
order by ticker, run_at desc

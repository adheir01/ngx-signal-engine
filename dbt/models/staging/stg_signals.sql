-- stg_signals.sql
-- Staging model joining signals with their LLM explanations

select
    s.id             as signal_id,
    s.ticker,
    s.trade_date,
    s.signal,
    s.signal_strength,
    s.triggered_rules,
    s.close_price::float    as close_price,
    s.rsi_14::float         as rsi_14,
    s.sma_crossover,
    s.volume_spike,
    s.generated_at,
    e.explanation,
    e.risk_flag,
    e.risk_reasoning
from {{ source('public', 'signals') }} s
left join {{ source('public', 'signal_explanations') }} e
    on s.id = e.signal_id

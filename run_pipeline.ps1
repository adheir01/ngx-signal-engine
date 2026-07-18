# run_pipeline.ps1
# Run full pipeline: dbt → signals
# Usage: .\run_pipeline.ps1

Write-Host "=== Running dbt feature layer ===" -ForegroundColor Green

$env:POSTGRES_HOST="127.0.0.1"
$env:POSTGRES_PORT="5436"
$env:POSTGRES_DB="ngx_signals"
$env:POSTGRES_USER="ngx_user"
$env:POSTGRES_PASSWORD="naija26"

Set-Location dbt
dbt run
Set-Location ..

Write-Host "=== Running signal pipeline ===" -ForegroundColor Green
docker-compose run --rm signals

Write-Host "=== Done ===" -ForegroundColor Green
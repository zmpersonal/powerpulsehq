# PowerPulseHQ v2 — U.S. Electricity Price & Cost Index

Static GitHub Pages site combining:

- U.S. residential electricity price index
- month-over-month, year-over-year and five-year price changes
- state electricity reports
- standardized Cost to Run Index for 15 equipment categories
- national rankings
- adjustable operating-cost calculator
- downloadable CSV + JSON datasets

## Required GitHub secret

`EIA_API_KEY`

Get a free key from the U.S. Energy Information Administration Open Data registration page.

## First deployment

1. Upload all files, including `.github`.
2. Settings → Pages → Source: GitHub Actions.
3. Add repository secret `EIA_API_KEY`.
4. Set custom domain `powerpulsehq.com`.
5. Actions → **Update PowerPulse data and deploy** → Run workflow.

The updater runs weekly, but EIA retail-price data are monthly. It deploys directly in the same workflow whenever it runs.

## Link architecture

The generated site contains exactly one followed outbound link to InHouseWellness.com, on `/home-wellness-equipment/`.

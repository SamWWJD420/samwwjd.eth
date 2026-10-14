# Keyword research

`kw.py` pulls Keyword Planner data (monthly volume, competition, top-of-page bids,
12-month history) through the Google Ads API and writes `ideas.csv`, ranked by
an opportunity score: volume × (1 + high bid) ÷ (1 + competition index / 25).

## Setup (one time)
1. Google Ads account (no spend needed). Create a manager (MCC) account if you
   don't have one; API Center lives under it: Admin → API Center.
2. Apply for a developer token there. A new token has **test access** only and
   can't read real data; apply for **Basic access** (form review, usually a few days).
3. Google Cloud project → enable "Google Ads API" → create an OAuth client
   (Desktop app). Generate a refresh token for your Google account, e.g. with
   `google-ads` Python lib's `generate_user_credentials.py` example.
4. Store these as environment secrets (not in this repo):
   `GADS_DEVELOPER_TOKEN`, `GADS_CLIENT_ID`, `GADS_CLIENT_SECRET`,
   `GADS_REFRESH_TOKEN`, `GADS_CUSTOMER_ID`, and `GADS_LOGIN_CUSTOMER_ID`
   if access goes through the MCC.
5. Allow `googleads.googleapis.com` and `oauth2.googleapis.com` in the
   environment's network policy.

## Run
    python3 kw.py              # seeds.txt -> ideas.csv
    python3 kw.py my.txt out.csv

Note: accounts with no ad spend may get bucketed volume ranges in the UI;
verify the API returns exact numbers on your account before trusting fine-grained ranks.

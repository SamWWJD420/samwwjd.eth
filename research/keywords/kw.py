#!/usr/bin/env python3
"""Keyword Planner sweep via the Google Ads API (REST, stdlib only).

Calls KeywordPlanIdeaService.GenerateKeywordIdeas for the seeds in seeds.txt
and writes ideas.csv sorted by an opportunity score.

Required env vars:
  GADS_DEVELOPER_TOKEN   developer token (Basic access or higher; test tokens
                         only work against test accounts, which return no real data)
  GADS_CLIENT_ID         OAuth client ID
  GADS_CLIENT_SECRET     OAuth client secret
  GADS_REFRESH_TOKEN     OAuth refresh token for a user with access to the account
  GADS_CUSTOMER_ID       Ads account ID to bill quota against, digits only
Optional:
  GADS_LOGIN_CUSTOMER_ID manager (MCC) account ID if access goes through one
  GADS_API_VERSION       default v25
  GADS_GEO               geo target constant, default 2840 (United States)
  GADS_LANGUAGE          language constant, default 1000 (English)

Usage: python3 kw.py [seeds.txt] [ideas.csv]
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://googleads.googleapis.com"
BATCH = 20  # GenerateKeywordIdeas accepts at most 20 seed keywords


def env(name, default=None):
    v = os.environ.get(name, default)
    if v is None:
        sys.exit(f"missing env var {name}")
    return v


def post(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {url}\n{e.read().decode()}")


def access_token():
    body = urllib.parse.urlencode({
        "client_id": env("GADS_CLIENT_ID"),
        "client_secret": env("GADS_CLIENT_SECRET"),
        "refresh_token": env("GADS_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }).encode()
    return post("https://oauth2.googleapis.com/token", body,
                {"Content-Type": "application/x-www-form-urlencoded"})["access_token"]


def load_seeds(path):
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def ideas(seeds, token):
    version = env("GADS_API_VERSION", "v25")
    customer = env("GADS_CUSTOMER_ID").replace("-", "")
    headers = {
        "Authorization": f"Bearer {token}",
        "developer-token": env("GADS_DEVELOPER_TOKEN"),
        "Content-Type": "application/json",
    }
    login = os.environ.get("GADS_LOGIN_CUSTOMER_ID")
    if login:
        headers["login-customer-id"] = login.replace("-", "")
    url = f"{API}/{version}/customers/{customer}:generateKeywordIdeas"

    out = {}
    for i in range(0, len(seeds), BATCH):
        page_token = None
        while True:
            body = {
                "language": f"languageConstants/{env('GADS_LANGUAGE', '1000')}",
                "geoTargetConstants": [f"geoTargetConstants/{env('GADS_GEO', '2840')}"],
                "keywordPlanNetwork": "GOOGLE_SEARCH",
                "includeAdultKeywords": False,
                "keywordSeed": {"keywords": seeds[i:i + BATCH]},
                "pageSize": 1000,
            }
            if page_token:
                body["pageToken"] = page_token
            resp = post(url, json.dumps(body).encode(), headers)
            for r in resp.get("results", []):
                out.setdefault(r["text"], r.get("keywordIdeaMetrics", {}))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        time.sleep(2)  # KeywordPlanIdeaService has tighter per-minute quotas
    return out


def row(text, m):
    vol = int(m.get("avgMonthlySearches", 0) or 0)
    comp_idx = int(m.get("competitionIndex", 0) or 0)
    high_bid = int(m.get("highTopOfPageBidMicros", 0) or 0) / 1e6
    monthly = [int(x.get("monthlySearches", 0) or 0) for x in m.get("monthlySearchVolumes", [])]
    # Trend: last 3 months vs the 3 before them.
    trend = ""
    if len(monthly) >= 6 and sum(monthly[-6:-3]):
        trend = round(sum(monthly[-3:]) / sum(monthly[-6:-3]) - 1, 2)
    # Opportunity: demand x commercial value, discounted by advertiser competition.
    score = round(vol * (1 + high_bid) / (1 + comp_idx / 25), 1)
    return {
        "keyword": text,
        "avg_monthly_searches": vol,
        "competition": m.get("competition", ""),
        "competition_index": comp_idx,
        "low_bid_usd": round(int(m.get("lowTopOfPageBidMicros", 0) or 0) / 1e6, 2),
        "high_bid_usd": round(high_bid, 2),
        "trend_3m": trend,
        "score": score,
    }


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    seeds_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "seeds.txt")
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "ideas.csv")
    rows = sorted((row(t, m) for t, m in ideas(load_seeds(seeds_path), access_token()).items()),
                  key=lambda r: r["score"], reverse=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["keyword"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} ideas -> {out_path}")


if __name__ == "__main__":
    main()

"""
pipeline/enrichment/__init__.py

Three enrichment sources, each independently improvable:

  apollo.py      — Contact data (email, title, LinkedIn URL, phone)
                   To improve: add phone reveal, org data (headcount, revenue)

  tavily.py      — Web search + news signals
                   To improve: add date filtering, source weighting, dedup

  brightdata.py  — Deep web: LinkedIn profile, SEC 13F AUM, company strategy, competitors
                   To improve: LinkedIn API proper, Pitchbook clone, Crunchbase scrape
"""

"""
pipeline/nodes/__init__.py

One file per pipeline node. Each node is independently testable.

  research.py  — Node 1: 5-source parallel enrichment
  distill.py   — Node 2: signal extraction + UNKNOWN signal gate
  score.py     — Node 3: informed scoring with AUM/title/LinkedIn rubric
  write.py     — Node 4: two-pass email writer with full dossier injection
  review.py    — Node 5: deterministic quality gate (word count, banned words)
  sync.py      — Node 6: CRM Lead + FCRM Note write-back
"""

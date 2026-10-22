#!/usr/bin/env python3
"""Record a review decision on observations or arrays (the reviewer is never the submitter).

  python scripts/review.py --reviewer "Name (ORCID)" --status reviewed_against_table  O1a2b3c4d5e6f A0123 ...
  python scripts/review.py --reviewer "Name" --status disputed --comment "paper says 3.1 m, not 3.2" O1a2b...

Statuses: see schema.REVIEW_STATUS. A 'reviewed_*' status requires reported_text on observations (the value as printed),
so that the check against the paper is auditable.  --list shows the unreviewed rows of one event.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema                                            # noqa: E402
from common import read_table, write_table              # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--reviewer")
    ap.add_argument("--status", choices=schema.REVIEW_STATUS)
    ap.add_argument("--comment", default="")
    ap.add_argument("--list", metavar="EVENT_ID")
    a = ap.parse_args()
    obs, arr = read_table("observations"), read_table("arrays")
    if a.list:
        for df, key in ((obs, "obs_id"), (arr, "array_id")):
            sub = df[(df.event_id == a.list) & (df.review_status == "draft")]
            for _, r in sub.iterrows():
                print(r[key], r.metric_id, r.pub_ids, r.get("statistic", "array"), r.get("value_num", ""), r.submitted_by)
        return
    if not (a.ids and a.reviewer and a.status):
        sys.exit("need ids, --reviewer and --status")
    today = dt.date.today().isoformat()
    for i in a.ids:
        for name, df, key in (("observations", obs, "obs_id"), ("arrays", arr, "array_id")):
            m = df[key] == i
            if not m.any():
                continue
            if df.loc[m, "submitted_by"].iloc[0].strip().lower() == a.reviewer.strip().lower():
                sys.exit(f"{i}: the reviewer cannot be the submitter")
            if a.status != "draft" and name == "observations" and not df.loc[m, "reported_text"].iloc[0]:
                sys.exit(f"{i}: add reported_text (the value as printed) before marking it reviewed")
            df.loc[m, ["review_status", "reviewed_by", "reviewed_on"]] = [a.status, a.reviewer, today]
            if a.comment and name == "observations":
                df.loc[m, "comment"] = (df.loc[m, "comment"].iloc[0] + " | " if df.loc[m, "comment"].iloc[0] else "") + a.comment
            break
        else:
            sys.exit(f"{i}: not found")
    write_table("observations", obs)
    write_table("arrays", arr)
    print(f"{len(a.ids)} row(s) marked {a.status}")


if __name__ == "__main__":
    main()

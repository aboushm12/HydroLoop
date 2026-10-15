"""Writes references.md from sources.json."""
import json, os
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(here, "..", "sources.json"), encoding="utf-8"))
used = {}
for e in S["ledger"]:
    used.setdefault(e["source_key"], []).append(e["key"])
lines = ["# References", "", f"Research date: {S['research_date']}. Evidence types: " + ", ".join(S["evidence_types"]) + ".", "",
         "Status: **verified** = values read from the source during the 2026-10-14 audit; **standard reference** = textbook/handbook values not re-read online; **not verified** = source identified but its values could not be read (not used numerically).", ""]
notv = {"DOI2014", "ER2026", "ER2024"}
std = {"FAO56", "DB", "ASHRAE_F", "ASHRAE621", "THIMIJAN", "CHISTI2007", "FLUIDS"}
for k, c in S["citations"].items():
    if k == "NONE":
        continue
    st = "not verified" if k in notv else ("standard reference - values from the handbook/textbook, not re-read online in this audit" if k in std else "verified")
    lines.append(f"- **[{k}]** {c['text']}" + (f" doi:{c['doi']}" if c["doi"] else "") + (f" <{c['url']}>" if c["url"] else "")
                 + f" — *{c['location']}*, {st}. Used for: `{', '.join(used.get(k, ['context only']))}`")
open(os.path.join(here, "..", "references.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("ok", len(lines))

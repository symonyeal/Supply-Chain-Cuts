"""Print the E1 sweep tables for FINDINGS §5: python analysis/sweep_table.py RUN_ID.

Rows (h, σ, L); for each α the number of minimal cut sets of support ≤ 3 at D_J = 12 and L.
Then one-at-a-time changes from the headline (tornado), ranked by |ΔL|.
"""
import json
import sys
from pathlib import Path

R = json.loads((Path("results") / sys.argv[1] / "risk.json").read_text(encoding="utf-8"))
C = R["configs"]
print("| h | σ | L (months) | α = 10%: cut sets | L | α = 25%: cut sets | L |")
print("| ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
for h in (0, 1, 3):
    for s, lead in ((0, 6), (0.1, 6), (0.1, 24), (0.5, 6), (0.5, 24)):
        row = [C[f"base_a{a}_h{h}_s{s}_L{lead}_D12"] for a in (0.1, 0.25)]
        print(f"| {h} | {s} | {lead if s else '–'} | " + " | ".join(
            f"{len(x['cuts'])} | {x['L']:.3f}" for x in row) + " |")
head = C["base_a0.25_h0_s0_L6_D12"]
moves = {"α = 10%": "base_a0.1_h0_s0_L6_D12", "α = 50%": "base_a0.5_h0_s0_L6_D12",
         "D ≤ 6": "base_a0.25_h0_s0_L6_D6", "D ≤ 3": "base_a0.25_h0_s0_L6_D3",
         "h = 1": "base_a0.25_h1_s0_L6_D12", "h = 3": "base_a0.25_h3_s0_L6_D12",
         **{f"σ = {s}, L = {lead}": f"base_a0.25_h0_s{s}_L{lead}_D12"
            for s in (0.1, 0.5) for lead in (6, 24)}}
print(f"\nHeadline: {len(head['cuts'])} cut sets, L = {head['L']:.3f}\n")
print("| Change from the headline | cut sets | L | ΔL |")
print("| --- | ---: | ---: | ---: |")
for k, key in sorted(moves.items(), key=lambda x: -abs(C[x[1]]["L"] - head["L"])):
    x = C[key]
    print(f"| {k} | {len(x['cuts'])} | {x['L']:.3f} | {x['L'] - head['L']:+.3f} |")

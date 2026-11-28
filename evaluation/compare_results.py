import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "evaluation" / "results"

d1 = json.loads(next(RES.glob("*top_k_1_detail.json")).read_text(encoding="utf-8"))
d3 = json.loads(next(RES.glob("*top_k_3_detail.json")).read_text(encoding="utf-8"))

m1 = {c["case_id"]: c for c in d1["cases"]}
m3 = {c["case_id"]: c for c in d3["cases"]}

print("题目  类别           k=1通过    k=3通过    k=1步数  k=3步数  k=1拒答  k=3拒答")
print("-" * 90)
for cid in m1:
    a, b = m1[cid], m3[cid]
    print(
        f"{cid:<5} {a['category']:<13} {str(a['passed']):<10} {str(b['passed']):<10} "
        f"{a['steps']:<8} {b['steps']:<8} {str(a['refused']):<8} {str(b['refused'])}"
    )

print("\n=== P3 在 k=1 下的答案（前 400 字） ===")
print(m1["P3"]["answer"][:400])
print("\n=== P3 在 k=3 下的答案（前 400 字） ===")
print(m3["P3"]["answer"][:400])
print("\n=== A3 在 k=1 下的答案（前 400 字） ===")
print(m1["A3"]["answer"][:400])

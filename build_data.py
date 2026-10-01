# -*- coding: utf-8 -*-
"""สร้างข้อมูลสำหรับเว็บสาธารณะ "ตำบลพร้อมรับมือ" (1 ต.ค. 2569)
Input : ผลทางการ SoVI v8 (store.pkl), หมู่บ้านประสบภัย ปภ. 2567 (ddpm2567_villages_by_tambon_v5.csv), ศูนย์พักพิง (CR_input xlsx, จันทบุรี), LISA (lisa_v8.pkl),
        ขอบเขตตำบลแบบลดทอนจากเว็บ SoVI-map (var GEO ใน index.html), เบอร์ อปท. (data/opt_contacts.csv ถ้ามี)
Output: data/tambons.json, data/tambons.geojson, js/leaflet.js, css/leaflet.css
กติกาสาธารณะ: ไม่มีอันดับ ไม่มีคะแนนดิบของดัชนี แสดงเฉพาะระดับ 5 ระดับและตัวเลขที่ชาวบ้านเข้าใจ"""
import os, re, json, pickle, sys, glob, numpy as np, pandas as pd
sys.path.insert(0, r"D:\PCA3\PCA3_updateboundary\PCA3_recal_newboundary\00_scripts"); import sovi_v8_core as C
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(os.path.join(HERE, "data"), exist_ok=True); os.makedirs(os.path.join(HERE, "js"), exist_ok=True); os.makedirs(os.path.join(HERE, "css"), exist_ok=True)
D = C.RUNDIR + r"\pooled_B_q1"; st = pickle.load(open(D + r"\store.pkl", "rb")); out = st["out"].copy(); LI = pickle.load(open(D + r"\lisa_v8.pkl", "rb"))["res"].set_index("pcode")
LEVEL = {"Very High": 5, "High": 4, "Moderate": 3, "Low": 2, "Very Low": 1}
# ---- ภัย 2567
dd = pd.read_csv(r"D:\PCA3\PCA3_updateboundary\SoVI_FinalReport_Chanthaburi_Rayong\_extract\ddpm2567_villages_by_tambon_v5.csv", encoding="utf-8-sig")
dd = dd[~dd["Subdistrict"].astype(str).str.startswith("เขตเทศบาล")].rename(columns={"District": "อำเภอ", "Subdistrict": "ตำบล"})
out = out.merge(dd[["จังหวัด", "อำเภอ", "ตำบล", "อุทกภัย", "วาตภัย", "ภัยแล้ง"]], on=["จังหวัด", "อำเภอ", "ตำบล"], how="left").fillna({"อุทกภัย": 0, "วาตภัย": 0, "ภัยแล้ง": 0})
# ---- ศูนย์พักพิง (จันทบุรี)
sh = pd.read_excel(glob.glob(r"E:\clauseAI\CR\CR_input\*ศูนย์พักพิง*.xlsx")[0], sheet_name="Sheet2")
sh.columns = [str(c).strip() for c in sh.columns]; sh = sh.iloc[:, :6]; sh.columns = ["no", "name", "จังหวัด", "อำเภอ", "ตำบล", "cap"]
sh = sh.dropna(subset=["name"]); sh["cap"] = pd.to_numeric(sh["cap"], errors="coerce")
shel = {}
for _, r in sh.iterrows(): shel.setdefault((str(r["จังหวัด"]).strip(), str(r["อำเภอ"]).strip(), str(r["ตำบล"]).strip()), []).append({"name": str(r["name"]).strip(), "cap": (int(r["cap"]) if pd.notna(r["cap"]) else None)})
# ---- เบอร์ อปท. (ถ้ามี)
cf = os.path.join(HERE, "data", "opt_contacts.csv"); contacts = {}
if os.path.exists(cf):
    cc = pd.read_csv(cf, encoding="utf-8-sig")
    for _, r in cc.iterrows():
        if str(r.get("สถานะ", "")).strip() != "พบ": continue
        contacts.setdefault(str(r["pcode"]), []).append({"name": str(r["อปท."]).strip(), "tel": str(r["โทรศัพท์"]).strip(), "web": (str(r["เว็บไซต์"]).strip() if pd.notna(r.get("เว็บไซต์")) and str(r.get("เว็บไซต์")).strip() not in ("", "nan") else "")})
# ---- ค่าเฉลี่ยจังหวัด (สำหรับประโยคเปรียบเทียบ)
pm = out.groupby("จังหวัด")[["V3_val", "V2_val", "V8_val", "V6_val", "V9_val", "V12_val", "V13_val", "V4_val"]].mean()
def cmp(v, m, hi_is_more=True):   # "สูงกว่า/ใกล้เคียง/ต่ำกว่า" ค่าเฉลี่ยจังหวัด (±10%)
    if m == 0: return "ใกล้เคียง"
    r = v / m
    return "สูงกว่า" if r > 1.1 else ("ต่ำกว่า" if r < 0.9 else "ใกล้เคียง")
recs = []
for _, r in out.iterrows():
    pv = r["จังหวัด"]; k = (pv, r["อำเภอ"], r["ตำบล"]); li = LI.loc[r["pcode"]]
    dom = max(["PC1", "PC2", "PC3"], key=lambda p: r[p]); pcs = {p: float(r[p]) for p in ["PC1", "PC2", "PC3"]}
    recs.append({
        "id": r["pcode"], "prov": pv, "amp": r["อำเภอ"], "tam": r["ตำบล"],
        "level": LEVEL[r["class"]],                       # 1 ต่ำมาก ... 5 สูงมาก (ไม่มีอันดับ)
        "dom": dom, "pc": {k_: round(v, 2) for k_, v in pcs.items()}, "pcflag": {p: ("สูง" if pcs[p] >= 0.5 else ("ต่ำ" if pcs[p] <= -0.5 else "กลาง")) for p in pcs},
        "cluster": {"สูง–สูง": "HH", "ต่ำ–ต่ำ": "LL", "สูง–ต่ำ": "HL", "ต่ำ–สูง": "LH"}.get(li["cluster"], "NS"),
        "pop": int(r["pop"]), "hh": int(r["hh"]), "regpop": int(r["reg_pop"]), "coverage": round(float(r["coverage_jpt_reg_%"]), 0),
        "eld_pct": round(float(r["V3_val"]), 1), "eld_cmp": cmp(r["V3_val"], pm.loc[pv, "V3_val"]),
        "child_pct": round(float(r["V2_val"]), 1), "child_cmp": cmp(r["V2_val"], pm.loc[pv, "V2_val"]),
        "dis_per100": round(float(r["V8_val"]), 2), "dis_cmp": cmp(r["V8_val"], pm.loc[pv, "V8_val"]),
        "lowedu_pct": round(float(r["V6_val"]), 0), "lowedu_cmp": cmp(r["V6_val"], pm.loc[pv, "V6_val"]),
        "income": int(round(float(r["V9_val"]), -2)), "income_cmp": cmp(r["V9_val"], pm.loc[pv, "V9_val"]),
        "nonet_pct": round(100 - float(r["V12_val"]), 0), "nonet_cmp": cmp(100 - r["V12_val"], 100 - pm.loc[pv, "V12_val"]),
        "nophone_pct": round(100 - float(r["V13_val"]), 1), "nophone_cmp": cmp(100 - r["V13_val"], 100 - pm.loc[pv, "V13_val"]),
        "eld_noinc": int(r["eld_noinc"]), "eld_n": int(r["eld"]),
        "flood": int(r["อุทกภัย"]), "storm": int(r["วาตภัย"]), "drought": int(r["ภัยแล้ง"]),
        "shelters": shel.get(k, []), "contacts": contacts.get(r["pcode"], []),
    })
meta = {"year": 2567, "updated": "1 ตุลาคม 2569", "n": len(recs), "prov_avg": {pv: {"eld_pct": round(float(pm.loc[pv, "V3_val"]), 1), "lowedu_pct": round(float(pm.loc[pv, "V6_val"]), 0), "income": int(round(float(pm.loc[pv, "V9_val"]), -2)), "nonet_pct": round(100 - float(pm.loc[pv, "V12_val"]), 0), "dis_per100": round(float(pm.loc[pv, "V8_val"]), 2)} for pv in pm.index},
        "levels": {str(i): n for i, n in enumerate(["", "เตรียมพร้อมตามปกติ", "เตรียมพร้อมตามปกติ และติดตามข่าว", "ควรเตรียมพร้อมเพิ่มขึ้น", "ควรเตรียมพร้อมเป็นพิเศษ", "ต้องเตรียมพร้อมเป็นพิเศษ และขอการสนับสนุน"], start=0) if i > 0},
        "level_counts": {str(LEVEL[c]): int(n) for c, n in out["class"].value_counts().items()}, "shelter_note": "ข้อมูลศูนย์พักพิงมีเฉพาะจังหวัดจันทบุรี (ข้อมูลระยองจะเพิ่มในระยะต่อไป)"}
json.dump({"meta": meta, "tambons": recs}, open(os.path.join(HERE, "data", "tambons.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ---- ขอบเขต: จาก SoVI-map GEO (ลดทอนแล้ว) ลดทอนเพิ่มเล็กน้อย
s = open(r"D:\PCA3\PCA3_updateboundary\SoVI-map\index.html", encoding="utf-8").read()
m = re.search(r"^var GEO=(\{.*\});\s*//", s, flags=re.M); GEO = json.loads(m.group(1))
from shapely.geometry import shape, mapping
feats = []
for f in GEO["features"]:
    g = shape(f["geometry"]).simplify(0.0012, preserve_topology=True); feats.append({"type": "Feature", "properties": {"id": f["properties"]["n"]}, "geometry": mapping(g)})
gj = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":"))
gj = re.sub(r"(\d+\.\d{5})\d+", r"\1", gj)   # 5 ตำแหน่งทศนิยม (~1 ม.)
open(os.path.join(HERE, "data", "tambons.geojson"), "w", encoding="utf-8").write(gj)
# ---- Leaflet (ฝังไว้ในเว็บ SoVI-map อยู่แล้ว) แยกเป็นไฟล์
L = s.split("\n"); js = [l for l in L if l.startswith("!function(t,e)")][0]; open(os.path.join(HERE, "js", "leaflet.js"), "w", encoding="utf-8").write(js)
i0 = s.find("<style>/* required styles */") + len("<style>"); i1 = s.find("</style>", i0); open(os.path.join(HERE, "css", "leaflet.css"), "w", encoding="utf-8").write(s[i0:i1])
print("tambons", len(recs), "| shelters tambons", sum(1 for r in recs if r["shelters"]), "| contacts", sum(1 for r in recs if r["contacts"]), "| geojson KB", len(gj) // 1024, "| level counts", meta["level_counts"])

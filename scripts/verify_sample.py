import json

d = json.load(open("data/latest.json", encoding="utf-8"))
seen = {}
for sec in d["sectors"]:
    for s in sec["stocks"]:
        seen[s["code"]] = s

print(f"資料日期：{d['date']}")
print(f"回補交易日數：{d['trading_days']}")
print(f"對帳誤差率：{d['reconciliation']['error_ratio']:.4%}")
print(f"板塊總數：{len(d['sectors'])}")

for code in ["2330", "2317", "5483"]:
    s = seen.get(code)
    if s:
        print(f"{s['code']} {s['name']} ({s['market']}) 收盤={s['close']} 法人淨買超={s['net_1d_yi']:.4f} 億")

print("\n前 5 大近 5 日買超板塊：")
for sec in d["sectors"][:5]:
    print(f"- {sec['name']} ({sec['quadrant']}): 近5日={sec['net_5d_yi']:.2f}億, 加速度={sec['accel']:.2f}, 檔數={sec['size']}")

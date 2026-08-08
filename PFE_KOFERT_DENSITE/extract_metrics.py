# extract_metrics.py
import json, csv
metrics = json.load(open("PFE_KOFERT_DENSITE/model/saved/metrics_forward_all.json","r",encoding="utf-8"))
rows=[]
for e, m in metrics.items():
    rows.append([e, m.get("n_train"), m.get("n_test"), m.get("mae"), m.get("r2")])
with open("metrics_table.csv","w",newline="") as fh:
    writer=csv.writer(fh)
    writer.writerow(["echelon","n_train","n_test","mae","r2"])
    writer.writerows(rows)
print("metrics_table.csv créé")
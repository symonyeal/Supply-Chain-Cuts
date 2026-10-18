"""Inspect concordance and act fields before specifying cohort code."""
import json
from pathlib import Path
import xlrd

r = Path('C:/Users/Yeal/Documents/My Projects/Chokepoint-Lab')
s = xlrd.open_workbook(r/'data/raw/hs/HS12_HS07.xls').sheet_by_index(0)
for row in (s.row_values(i) for i in range(2, s.nrows)):
    if row[2] in ('250410', '260500', '280461', '283691', '282520', '750210'):
        print(row)
print(json.dumps(json.loads((r/'data/events/acts.yaml').read_text())['acts'][0], indent=1))

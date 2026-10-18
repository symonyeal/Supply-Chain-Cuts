"""Inspect the frozen UN workbook's schema, not severity outcomes."""
from pathlib import Path
import xlrd

p = Path('C:/Users/Yeal/Documents/My Projects/Chokepoint-Lab/data/raw/hs/HS12_HS07.xls')
b = xlrd.open_workbook(p)
for s in b.sheets():
    print(s.name, s.nrows, s.ncols)
    for r in range(min(7, s.nrows)):
        print(s.row_values(r))

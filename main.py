import pandas as pd
from core import enrich_company_info

icos = ['00177041','29137624','45317054','25148290','26764652','45317054']  # přidej IČA

results = []
for ico in icos:
    info = enrich_company_info(ico)
    if info:
        results.append(info)

df = pd.DataFrame(results)
df.to_csv("vystup.csv", index=False)
print(df)


# Škoda Auto a.s. – IČO: 00177041
# glix.cz+14Wikipedia+14Škoda Auto+14
#
# Komerční banka, a.s. – IČO: 45317054
# petr-necas.cz+7Měšec.cz+7Finmag+7
#
# ESSEX, určitě firma řekněme Factoring KB, a.s. – IČO: 25148290
# Škoda Auto+15glix.cz+15Finmag+15
#
# ESSOX s.r.o. – IČO: 26764652
# glix.cz
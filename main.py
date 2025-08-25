import pandas as pd
from core import enrich_company_info,core_test_GPT
from coreCL import Company

# icos = ['00177041','29137624','45317054','25148290','26764652','45317054']  # přidej IČA
#
# results = []
# for ico in icos:
#     info = enrich_company_info(ico)
#     if info:
#         results.append(info)
#
# df = pd.DataFrame(results)
# df.to_csv("vystup.csv", index=False)
# print(df)

#core_test_GPT()



if __name__ == "__main__":

    ico_list = [ "71447687", "28750713", "17241201", "65424255", "11800721", "05484545", "03583058", "06154361", "76098877", "27571556", "71465201", "03425002", "65119665", "75848856", "45981868", "22026975", "21124833", "27301656", "05599954", "25913000", "73282138", "74099761", "63290006", "62607618", "67797687", "21889848", "76266656", "49214403", "86708074", "01526006", "44867921", "62007157", "73522546", "49521098", "87390361", "05392161", "62974980", "22674802", "44014422", "07293399", "05419808", "05753937", "09375384", "13688642", "28407288", "04155599", "21932867", "00975818", "74368125", "07032587" ]

    #ico_list = ['00177041','29137624','45317054']  # příklad: KB, Škoda Auto, ČEZ
    for ico in ico_list:
        firma = Company(ico)
        try:
            firma.fetch_from_ares()
            #firma.find_website()
            #firma.scrape_website_text()
            #firma.classify_keyword()  # nebo
            firma.classify_gpt()
            #firma.save_to_json(f"{firma.ico}.json")
            firma.print_company()
        except Exception as e:
            print(f"Chyba u IČO {ico}:", e)



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
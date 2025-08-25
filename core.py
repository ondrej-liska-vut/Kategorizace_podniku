import requests
from bs4 import BeautifulSoup
from readability import Document
import re
from serpapi import GoogleSearch

import key
from key import serpapi_key
from categories import categories

import requests

def get_company_info_from_ares(ico):
    url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
    r = requests.get(url)

    if r.status_code != 200:
        print(f"Chyba {r.status_code} při dotazu na ARES.")
        return None

    data = r.json()

    return {
        'ico': ico,
        'name': data.get('obchodniJmeno'),
        'address': data.get('sidlo', {}).get('textovaAdresa'),
        'nace': data.get('primarniNace', {}).get('nazev'),
        'web': None  # stále není součástí dat
    }

# Test
#print(get_company_info_from_ares("45317054"))  # Komerční banka

def find_possible_website(company_name):
    # jednoduchý DuckDuckGo dotaz
    q = f"{company_name} site:.cz"
    r = requests.get("https://html.duckduckgo.com/html/", params={"q": q}, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    a_tag = soup.find("a", {"class": "result__a"})
    return a_tag['href'] if a_tag else None

def find_possible_website_serpapi(company_name):
    params = {
        "q": f"{company_name} oficiální web",
        "engine": "google",
        "api_key": serpapi_key #find in separate file
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    for res in results.get("organic_results", []):
        link = res.get("link", "")
        if ".cz" in link:
            return link
    return None

def get_website_text(url):
    try:
        r = requests.get(url, timeout=5)
        doc = Document(r.text)
        soup = BeautifulSoup(doc.summary(), "html.parser")
        return soup.get_text()
    except:
        return ""

def classify_companyOBS(text):
    text = text.lower()

    for category, keywords in categories.items():
        for kw in keywords:
            if kw in text:
                return category
    return "Neznámá"

def classify_company(text):
    print(text)
    text = text.lower()
    score_table = {}

    for category, keywords in categories.items():
        score = 0
        for kw in keywords:
            # spočítá výskyt slova v textu (přesná slova, ne jen podřetězce)
            matches = re.findall(rf"\b{re.escape(kw.lower())}\b", text)
            score += len(matches)
        score_table[category] = score

    # Vybere kategorii s nejvyšším počtem shod
    best_category = max(score_table, key=score_table.get)
    return best_category if score_table[best_category] > 0 else "Neznámá"

def enrich_company_info(ico):
    ico = ico.strip()
    if not ico.isdigit() or len(ico) != 8:
        print(f"IČO {ico} je neplatné.")
        return None

    info = get_company_info_from_ares(ico)
    if info is None:
        print(f"IČO {ico} se nepodařilo načíst z ARES.")
        return None

    print(f"Zpracovávám {info['name']}...")

    #website = find_possible_website(info['name'])
    website = find_possible_website_serpapi(info['name'])
    info['website'] = website

    if website:
        text = get_website_text(website)
        info['category'] = classify_company(text)
    else:
        info['category'] = "Nenalezeno"

    return info

from openai import OpenAI

client = OpenAI(api_key=key.open_ai_key)  # nebo zadej natvrdo jako api_key="sk-..."

def classify_with_gpt(company_name, nace, address, categories):
    system_message = "Jsi expert na třídění firem podle jejich oboru činnosti."

    user_prompt = f"""
Na základě následujících údajů o firmě vyber jednu nejvhodnější kategorii ze seznamu:

Seznam kategorií:
{", ".join(categories)}

Název firmy: {company_name}
NACE (obor): {nace}
Adresa: {address}

Odpověz pouze názvem jedné kategorie ze seznamu, bez dalších komentářů.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # nebo gpt-3.5-turbo
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Chyba při volání OpenAI:\n", e)
        return "Neurčeno"

def core_test_GPT():
    ct = list(categories.keys())  # ze slovníku načti jen názvy kategorií

    result = classify_with_gpt(
        company_name="Komerční banka, a.s.",
        nace="Bankovnictví",
        address="Na Příkopě 969/33, Praha 1",
        categories=ct
    )

    print("GPT navržená kategorie:", result)

# def classify_company_by_ares_gpt(ico, categories):
#     info = get_company_info_from_ares(ico)
#     if info is None:
#         return "N/A"
#
#     prompt = f"""Na základě následujících údajů o firmě se pokus klasifikovat firmu do jedné z následujících kategorií:
# {', '.join(categories)}.
#
# Název firmy: {info['name']}
# NACE (obor): {info['nace']}
# Sídlo: {info['address']}
#
# Vrátíš pouze název jedné nejvhodnější kategorie.
# """
#
#     try:
#         completion = openai.ChatCompletion.create(
#             model="gpt-4",  # nebo gpt-3.5-turbo
#             messages=[
#                 {"role": "system", "content": "Jsi expert na třídění firem podle oboru podnikání."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.2,
#         )
#         return completion.choices[0].message.content.strip()
#     except Exception as e:
#         print("Chyba LLM:", e)
#         return "Chyba"

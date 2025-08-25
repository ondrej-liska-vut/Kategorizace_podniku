import requests
from bs4 import BeautifulSoup
from readability import Document
import re
import json
from serpapi import GoogleSearch
from openai import OpenAI
import pandas as pd

import key
from key import serpapi_key
from categories import categories

client = OpenAI(api_key=key.open_ai_key)

class Company:
    def __init__(self, ico, name=None, address=None, nace=None, website=None, web_text=None, category=None):
        self.ico = ico
        self.name = name
        self.address = address
        self.nace = nace
        self.website = website
        self.web_text = web_text
        self.category = category

    def to_dict(self):
        return {
            "ico": self.ico,
            "name": self.name,
            "address": self.address,
            "nace": self.nace,
            "website": self.website,
            "category": self.category
        }

    @staticmethod
    def from_dict(data):
        return Company(**data)

    def save_to_json(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_from_json(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return Company.from_dict(data)

    def fetch_from_ares(self):
        url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{self.ico}"
        r = requests.get(url)
        if r.status_code != 200:
            raise Exception(f"ARES error {r.status_code}")
        data = r.json()
        self.name = data.get('obchodniJmeno')
        self.address = data.get('sidlo', {}).get('textovaAdresa')
        self.nace = data.get('primarniNace', {}).get('nazev')

    def find_website(self):
        params = {
            "q": f"{self.name} oficiální web",
            "engine": "google",
            "api_key": serpapi_key
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        for res in results.get("organic_results", []):
            link = res.get("link", "")
            if ".cz" in link:
                self.website = link
                return
        self.website = None

    def scrape_website_text(self):
        if not self.website:
            self.web_text = ""
            return
        try:
            r = requests.get(self.website, timeout=5)
            doc = Document(r.text)
            soup = BeautifulSoup(doc.summary(), "html.parser")
            self.web_text = soup.get_text()
        except:
            self.web_text = ""

    def classify_keyword(self):
        text = (self.web_text or "").lower()
        score_table = {}
        for category, keywords in categories.items():
            score = 0
            for kw in keywords:
                matches = re.findall(rf"\b{re.escape(kw.lower())}\b", text)
                score += len(matches)
            score_table[category] = score
        best = max(score_table, key=score_table.get)
        self.category = best if score_table[best] > 0 else "Neznámá"

    def classify_gpt(self):
        system_message = "Jsi expert na třídění firem podle jejich oboru činnosti."
        prompt = f"""
Na základě následujících údajů o firmě vyber jednu nejvhodnější kategorii ze seznamu:

Seznam kategorií:
{', '.join(categories.keys())}

Název firmy: {self.name}
NACE (obor): {self.nace}
WEB: {self.website}
Adresa: {self.address}

Odpověz pouze názvem jedné kategorie ze seznamu, bez dalších komentářů.
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            self.category = response.choices[0].message.content.strip()
        except Exception as e:
            print("Chyba při volání OpenAI:", e)
            self.category = "Neurčeno"

    def print_company(self):
        print("Název:", self.name)
        print("IČO:", self.ico)
        print("Adresa:", self.address)
        print("NACE:", self.nace)
        print("Web:", self.website)
        print("Kategorie:", self.category)
        print("-" * 40)

def process_companies(ico_list):
    results = []
    for ico in ico_list:
        firma = Company(ico)
        try:
            firma.fetch_from_ares()
            firma.find_website()
            firma.scrape_website_text()
            firma.classify_keyword()
            firma.classify_gpt()
            results.append(firma.to_dict())
        except Exception as e:
            print(f"Chyba u IČO {ico}:", e)
    return results

if __name__ == "__main__":
    ico_list = [
        "71447687", "28750713", "17241201", "65424255", "11800721", "05484545", "03583058", "06154361",
        "76098877", "27571556", "71465201", "03425002", "65119665", "75848856", "45981868", "22026975",
        "21124833", "27301656", "05599954", "25913000", "73282138", "74099761", "63290006", "62607618",
        "67797687", "21889848", "76266656", "49214403", "86708074", "01526006", "44867921", "62007157",
        "73522546", "49521098", "87390361", "05392161", "62974980", "22674802", "44014422", "07293399",
        "05419808", "05753937", "09375384", "13688642", "28407288", "04155599", "21932867", "00975818",
        "74368125", "07032587"
    ]

    data = process_companies(ico_list)
    df = pd.DataFrame(data)
    print(df)
    df.to_csv("companies_categorized.csv", index=False, encoding="utf-8")

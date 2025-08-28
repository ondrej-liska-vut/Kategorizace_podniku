import requests
from bs4 import BeautifulSoup
from readability import Document
import re
import json
from serpapi import GoogleSearch
from openai import OpenAI
import openai
import pandas as pd

import google.generativeai as genai
import key
from categories import categories
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import cohere

client = OpenAI(api_key=key.open_ai_key)
co = cohere.Client(key.cohere_api_key)
anthropic_client = Anthropic(api_key=key.anthropic_api_key)
mistral_client = openai.OpenAI(api_key=key.together_api_key, base_url="https://api.together.xyz/v1")
genai.configure(api_key=key.google_api_key)

class Company:
    def __init__(
            self,
            ico,
            name=None,
            address=None,
            nace=None,
            website=None,
            web_text=None,
            category_keyword=None,
            category_gpt=None,
            category_claude=None,
            category_cohere=None,
            category_mistral=None,
            category_per=None
    ):
        self.ico = ico
        self.name = name
        self.address = address
        self.nace = nace
        self.website = website
        self.web_text = web_text

        # Výstupy z klasifikací
        self.category_keyword = category_keyword
        self.category_GPT = category_gpt
        self.category_claude = category_claude
        self.category_cohere = category_cohere
        self.category_mistral = category_mistral
        self.category_per = category_per
        self.per_reason = None
        self.category_google = None

    def to_dict(self):
        return {
            "ico": self.ico,
            "name": self.name,
            "address": self.address,
            "nace": self.nace,
            "website": self.website,
            "c_keyword": self.category_keyword,
            "c_gpt": self.category_GPT,
            "c_claude": self.category_claude,
            "c_cohere": self.category_cohere,
            "c_mistral": self.category_mistral,
            "perplexity":self.category_per,
            "perplexity_reasoning":self.per_reason,
            "G-AI":self.category_google
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            ico=data.get("ico"),
            name=data.get("name"),
            address=data.get("address"),
            nace=data.get("nace"),
            website=data.get("website"),
            category_keyword=data.get("category_keyword"),
            category_gpt=data.get("category_gpt"),
            category_claude=data.get("category_claude"),
            category_cohere=data.get("category_cohere"),
            category_mistral=data.get("category_mistral"),
            category_per = data.get("category_per")
        )

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
        self.nace = data.get('czNace')
        t=4

    def find_website(self):
        params = {
            "q": f"{self.name} oficiální web",
            "engine": "google",
            "api_key": key.serpapi_key
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
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(self.website, headers=headers, timeout=5)

            if r.status_code != 200 or not r.text.strip():
                print(f"⚠️ Chybný nebo prázdný obsah z {self.website}")
                self.web_text = ""
                return

            if "text/html" not in r.headers.get("Content-Type", ""):
                print(f"⚠️ Nejedná se o HTML stránku: {self.website}")
                self.web_text = ""
                return

            doc = Document(r.text)
            soup = BeautifulSoup(doc.summary(), "html.parser")
            self.web_text = soup.get_text()

        except Exception as e:
            print(f"❌ Chyba při zpracování stránky {self.website}:\n{e}")
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
        self.category_keyword = best if score_table[best] > 0 else "Neznámá"

    def classify_gpt(self):
        system_message = "Jsi expert na třídění firem podle jejich oboru činnosti."
        prompt = generate_classification_prompt(self.name, self.nace, self.address, self.website, categories)

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            self.category_GPT = response.choices[0].message.content.strip()
        except Exception as e:
            print("Chyba při volání OpenAI:", e)
            self.category_GPT = "Neurčeno"

    def classify_claude_2(self):
        prompt = generate_classification_prompt(self.name, self.nace, self.address, self.website, categories)

        try:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            self.category_claude = response.content[0].text.strip()
        except Exception as e:
            print("Chyba při volání Claude API:", e)
            self.category_claude = "Neurčeno"

    def classify_mistral(self):
        prompt = generate_classification_prompt(self.name, self.nace, self.address, self.website, categories)

        try:
            response = mistral_client.chat.completions.create(
                model="mistralai/Mistral-7B-Instruct-v0.2",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            self.category_mistral = response.choices[0].message.content.strip()
        except Exception as e:
            print("Chyba při volání Mistral API:", e)
            self.category_mistral = "Neurčeno"

    def classify_cohere(self):
        prompt = generate_classification_prompt(self.name, self.nace, self.address, self.website, categories)

        try:
            response = co.chat(
                model="command-r",
                message=prompt,
                temperature=0.3
            )
            self.category_cohere = response.text
        except Exception as e:
            print("Chyba při volání Cohere API:", e)
            self.category_cohere = "Neurčeno"

    def print_company(self):
        print("Název:", self.name)
        print("IČO:", self.ico)
        print("Adresa:", self.address)
        print("NACE:", self.nace)
        print("Web:", self.website)
        print("Kategorie_keyword:", self.category_keyword)
        print("Kategorie_GPT:", self.category_GPT)
        print("-" * 40)

    def classify_with_perplexity(self):
        api_key = key.perplexity_api_key

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""
Na základě těchto údajů o firmě určete jednu nejvhodnější kategorii z uvedeného seznamu:

Seznam kategorií:
{', '.join(categories.keys())}

Název: {self.name}
NACE: {self.nace}
Adresa: {self.address}

Odpověz pouze jednoslovněm názvem kategorie bez komentářů. Nveracej mi proces přemýšlení, pouze tu jednu kategorii bez dalšího komentáře!
"""

        data = {
            "model": "sonar-deep-research",  # nebo "sonar-pro"
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "search": True,  # webové hledání povoleno
            "stream": False
        }

        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip()
            self.per_reason = answer
            self.category_per = extract_last_nonempty_line(answer)
        else:
            print("Chyba z Perplexity:", response.status_code, response.text)
            self.category_per = "Neurčeno"

    import google.generativeai as genai

    # Inicializace (někde ve tvém kódu po importu klíče)
    genai.configure(api_key=key.google_api_key)  # klíč si dej do souboru key.py

    # ...

    def classify_google_ai(self):
        prompt = generate_classification_prompt(self.name, self.nace, self.address, self.website, categories)
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Extrahujeme poslední neprázdný řádek
            last_line = text.strip().splitlines()[-1]
            self.category_google = last_line
        except Exception as e:
            print("Chyba při volání Google Gemini API:", e)
            self.category_google = "Neurčeno"


def extract_last_nonempty_line(text):
    lines = text.strip().splitlines()
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return "Neurčeno"


def generate_classification_prompt(company_name, nace, address, website, categories_dict, web_text = None):
    if web_text == None:
        return f"""
Na základě následujících údajů o firmě vyber jednu nejvhodnější kategorii ze seznamu:

Seznam kategorií:
{', '.join(categories_dict.keys())}

Název firmy: {company_name}
NACE (obor): {nace}
WEB: {website}
Adresa: {address}

Odpověz pouze názvem jedné kategorie ze seznamu, bez dalších komentářů.
"""
    else:
        return f"""
Na základě následujících údajů o firmě:

Název firmy: {company_name}
NACE (obor): {nace}
WEB: {website}
Adresa: {address}

Vyber jednu nejvhodnější kategorii ze seznamu:
Seznam kategorií:
{', '.join(categories_dict.keys())}

Odpověz pouze názvem jedné kategorie ze seznamu, bez dalších komentářů.

Pro lepší určení použíj ještě informace z webové stránky:
{web_text}

Nevymýšlej si, pokud nevíš, tak to napiš.
"""

def process_companies(ico_list):
    results = []
    for ico in ico_list:
        firma = Company(ico)
        try:
            firma.fetch_from_ares()
            # firma.find_website()
            # firma.scrape_website_text()
            # firma.classify_keyword()
            # firma.classify_gpt()
            # firma.classify_cohere()
            # firma.classify_claude_2()
            # firma.classify_mistral()
            firma.classify_google_ai()
            #firma.classify_with_perplexity()
            results.append(firma.to_dict())
            print(f"hotovo {ico}")
        except Exception as e:
            print(f"Chyba u IČO {ico}:", e)
    return results

if __name__ == "__main__":
    ico_list = ["71447687", "28750713", "17241201", "65424255", "11800721", "05484545", "03583058", "06154361","76098877", "27571556", "71465201", "03425002", "65119665", "75848856", "45981868", "22026975","21124833", "27301656", "05599954", "25913000", "73282138", "74099761", "63290006", "62607618","67797687", "21889848", "76266656", "49214403", "86708074", "01526006", "44867921", "62007157","73522546", "49521098", "87390361", "05392161", "62974980", "22674802", "44014422", "07293399","05419808", "05753937", "09375384", "13688642", "28407288", "04155599", "21932867", "00975818","74368125", "07032587" ]

    #ico_list = ["28407288"]

    data = process_companies(ico_list)
    df = pd.DataFrame(data)
    print(df)
    df.to_csv("companies_categorized_search.csv", index=False, encoding="utf-8")


# Můžeš teď kliknout na ▶ vedle této funkce

# , "17241201", "65424255", "11800721", "05484545", "03583058", "06154361",
#         "76098877", "27571556", "71465201", "03425002", "65119665", "75848856", "45981868", "22026975",
#         "21124833", "27301656", "05599954", "25913000", "73282138", "74099761", "63290006", "62607618",
#         "67797687", "21889848", "76266656", "49214403", "86708074", "01526006", "44867921", "62007157",
#         "73522546", "49521098", "87390361", "05392161", "62974980", "22674802", "44014422", "07293399",
#         "05419808", "05753937", "09375384", "13688642", "28407288", "04155599", "21932867", "00975818",
#         "74368125", "07032587"

#TODO ověřit co vyhodí GPT když se ho zeptám přes prohlížeč

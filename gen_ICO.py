import random
import requests
import json
import time

def generate_valid_ico():
    base = [random.randint(0, 9) for _ in range(7)]
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(w * d for w, d in zip(weights, base))
    remainder = total % 11
    if remainder == 0:
        check_digit = 1
    elif remainder == 1:
        check_digit = 0
    else:
        check_digit = 11 - remainder
    base.append(check_digit)
    return ''.join(map(str, base))

def check_ico_in_ares(ico):
    url = f"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
    r = requests.get(url)
    if r.status_code == 200 and r.json().get("obchodniJmeno"):
        return True
    return False

def generate_and_save_icos(n=100, pause=0.3):
    found_icos = []
    tried = set()

    while len(found_icos) < n:
        ico = generate_valid_ico()
        if ico in tried:
            continue
        tried.add(ico)

        if check_ico_in_ares(ico):
            print(f"✔️  Nalezeno: {ico}")
            found_icos.append(ico)
        else:
            print(f"✖️  Nenalezeno: {ico}")

        time.sleep(pause)  # kvůli šetrnosti k ARES serveru

    with open("valid_ico.json", "w", encoding="utf-8") as f:
        json.dump(found_icos, f, ensure_ascii=False, indent=2)

    print(f"\nHotovo. Uloženo {len(found_icos)} platných IČO do valid_ico.json")

# Spuštění
if __name__ == "__main__":
    generate_and_save_icos(n=50)
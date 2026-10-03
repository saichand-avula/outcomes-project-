"""Print unused phone numbers and DOB-year/month suggestions so new calls never collide.
Usage: python3 code/data/fresh.py [n]"""
import random
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2] / "data" / "authoring"
txt = "\n".join(p.read_text() for p in root.rglob("*.yaml"))
used_p = set(re.findall(r'callback_phone_true: "(\d{10})"', txt))
used_d = set(re.findall(r'patient_dob_true: "(\d{4}-\d\d-\d\d)"', txt))
names = set(re.findall(r"(?:patient|caller)_name_true: (.+)", txt))
n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
rng = random.Random()
areas = ["212", "312", "404", "505", "602", "615", "713", "808", "919", "206", "303", "414", "503", "610", "704", "816", "901", "918", "314", "646"]
ph = []
while len(ph) < n:
    c = f"{rng.choice(areas)}555{rng.randint(100, 199):04d}"
    if c not in used_p and c not in ph:
        ph.append(c)
print("phones:", " ".join(ph))
print("(dob: pick any date; if it collides the validator says so)")
print("used dobs count", len(used_d), "used names", len(names))

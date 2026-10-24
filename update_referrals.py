#!/usr/bin/env python3
"""
🔗 Auto-Update Referral Links in README.md
Edit referrals.json with your personal referral URLs, then run:
  python update_referrals.py
"""

import json
import os
import re

REF_FILE = "referrals.json"
README_FILE = "README.md"

def main():
    if not os.path.exists(REF_FILE):
        print(f"File {REF_FILE} not found.")
        return
    if not os.path.exists(README_FILE):
        print(f"File {README_FILE} not found.")
        return

    with open(REF_FILE, "r", encoding="utf-8") as f:
        refs = json.load(f)

    with open(README_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    updated_count = 0
    for app_name, new_url in refs.items():
        pattern = re.compile(r"(\[\*\*" + re.escape(app_name) + r"\*\*\]\()([^)]+)(\))")
        if pattern.search(content):
            content = pattern.sub(r"\g<1>" + new_url + r"\g<3>", content)
            updated_count += 1

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Successfully updated {updated_count} referral links in {README_FILE}!")

if __name__ == "__main__":
    main()

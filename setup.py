#!/usr/bin/env python3
"""Generate a .env file from .env.example with a random SESSION_SECRET."""

import os
import re
from secrets import token_hex

src = ".env.example"
dst = ".env"

if not os.path.exists(src):
    print(f"{src} not found. Cannot generate {dst}.")
    raise SystemExit(1)

if os.path.exists(dst):
    print(f"{dst} already exists. Delete it first to regenerate.")
    raise SystemExit(1)

with open(src, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r"^SESSION_SECRET=.*$",
    f"SESSION_SECRET={token_hex(32)}",
    content,
    flags=re.M,
)

with open(dst, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Created {dst} with a random SESSION_SECRET.")
print("Remember to fill in GITHUB_CLIENT_SECRET before starting the app.")

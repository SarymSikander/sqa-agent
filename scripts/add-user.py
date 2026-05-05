#!/usr/bin/env python3
"""
Generate a bcrypt-hashed user entry for SQA_USERS.

Usage:
    python3 scripts/add-user.py email@example.com yourpassword

Output:
    {"email": "email@example.com", "password": "$2b$12$..."}

Copy the output and add it to the SQA_USERS JSON array in your
environment variables (HF Space secrets or .env file).
"""
import sys
import json
import bcrypt


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/add-user.py <email> <password>", file=sys.stderr)
        sys.exit(1)

    email = sys.argv[1].strip()
    password = sys.argv[2].encode()
    hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode()
    print(json.dumps({"email": email, "password": hashed}))


if __name__ == "__main__":
    main()

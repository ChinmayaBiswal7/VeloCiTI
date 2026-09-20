"""Print a TEAM_MEMBERS value with hashed passwords.

Usage: python make_team_members.py email:password [email:password ...]
Paste the output into the TEAM_MEMBERS environment variable (for example on Render).
"""
import hashlib
import json
import sys


def main(args):
    if not args:
        sys.exit(__doc__)
    members = []
    for arg in args:
        email, _, password = arg.partition(":")
        if not email or not password:
            sys.exit(f"Expected email:password, got {arg!r}")
        members.append({
            "email": email,
            "password_sha256": hashlib.sha256(password.strip().encode("utf-8")).hexdigest(),
            "name": "",
            "role": "System Operator",
            "badge": "",
            "department": "Traffic Operations",
        })
    print(json.dumps(members))


if __name__ == "__main__":
    main(sys.argv[1:])

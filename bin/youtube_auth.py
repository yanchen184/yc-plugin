"""Standalone OAuth bootstrap for yc-plugin.

Forces a browser auth flow and saves token to plugin data dir.
Usually you don't need this — the upload script auto-runs auth on first use.
Use this only if you want to re-auth without touching upload code.
"""
from lib import console, youtube_client


def main():
    console.init()
    creds = youtube_client.get_credentials()
    console.ok(f"authenticated. token at {youtube_client.token_file()}")


if __name__ == "__main__":
    # Add token_file accessor for the print
    from lib.paths import token_file
    youtube_client.token_file = token_file
    main()

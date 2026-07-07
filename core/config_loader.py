import sys

# Smart fallback configuration check
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

def load_config():
    """Loads and returns the project TOML configuration framework safely."""
    try:
        with open("config.toml", "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print("❌ Error: config.toml not found. Please create one based on the documentation templates.")
        sys.exit(1)
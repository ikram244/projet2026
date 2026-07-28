import os

EXCLUDE = {"venv2", "venv", "__pycache__", ".git", "node_modules", ".vscode", "raw"}

def print_tree(path, prefix=""):
    entries = sorted(os.listdir(path))
    entries = [e for e in entries if e not in EXCLUDE and not e.startswith(".")]
    for i, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        connector = "└── " if i == len(entries) - 1 else "├── "
        print(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "    " if i == len(entries) - 1 else "│   "
            print_tree(full_path, prefix + extension)

print_tree(".")
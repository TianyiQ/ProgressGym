import os, sys
root = "src".join(os.path.dirname(os.path.abspath(__file__)).split("src")[:-1]).rstrip("/").rstrip("\\")
print(f"Library root directory: {root}")
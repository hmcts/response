import ast
import astor
import fileinput
import os

# Path to the setup.py file
setup_file_path = "setup.py"

# New version value
new_version = os.environ["NEW_VERSION"]

# Update the value of VERSION in the file
with fileinput.FileInput(setup_file_path, inplace=True) as file:
    for line in file:
        if line.startswith("VERSION"):
            old_version = line.split("'")[1]
            line = f"VERSION = '{new_version}'\n"
        print(line, end='')

    if old_version != new_version:
        print(f"version_updated")
    else:
        print(f"version_unchanged")



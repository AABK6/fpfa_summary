import os
import argparse

# Define the directory to scan and the output file
parser = argparse.ArgumentParser(description="Combine code files into one text file.")
parser.add_argument('--nodir', action='store_true', help='Exclude all subdirectories from scan')
parser.add_argument('--exclude', default="", help='Comma separated list of subdirectory names to exclude in addition to defaults')
args = parser.parse_args()

base_dir = os.getcwd()  # Set base directory as current working directory
output_file = os.path.join(base_dir, 'all_code.txt')

# Extensions to include
extensions = {'.py', '.js', '.java', '.html', '.css', '.yaml', '.md'}

# Default directories and files to exclude
default_exclude_dirs = {'.env', '.venv', '__pycache__', '.git'}
default_exclude_files = {'.gitignore'}

# Combine user-specified exclude dirs if provided
exclude_dirs = set(default_exclude_dirs)
if args.exclude:
    exclude_dirs.update({d.strip() for d in args.exclude.split(',') if d.strip()})

with open(output_file, 'w', encoding='utf-8') as outfile:
    for root, dirs, files in os.walk(base_dir):
        # If excluding all subdirectories, skip any root that's not the base directory
        if args.nodir and root != base_dir:
            continue
        # Remove any directories that should be excluded
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file in default_exclude_files:
                continue
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                # Write a header line with the file path
                outfile.write(f"\n##### START FILE: {file_path} #####\n\n")
                with open(file_path, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                outfile.write(f"\n##### END FILE: {file_path} #####\n\n\n")

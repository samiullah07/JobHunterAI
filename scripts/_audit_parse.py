import ast
import pathlib
import sys

def check_file(path):
    try:
        content = path.read_text(encoding='utf-8')
        ast.parse(content)
        return None
    except SyntaxError as e:
        return f"PARSE FAIL: {path}: {e}"
    except Exception as e:
        return f"ERROR: {path}: {e}"

def main():
    # Collect all Python files from all relevant directories
    directories = ['src', 'frontend', 'scripts', 'tests']
    all_files = []
    for dir_path in directories:
        dir_obj = pathlib.Path(dir_path)
        if dir_obj.exists():
            all_files.extend(dir_obj.rglob('*.py'))

    failures = []
    for file_path in all_files:
        error = check_file(file_path)
        if error:
            failures.append(error)

    if failures:
        print('\n'.join(failures))
        sys.exit(1)
    else:
        print('ALL PARSE OK')

if __name__ == '__main__':
    main()
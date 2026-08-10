content = open('frontend/app.py', encoding='utf-8').read()
old = "except Exception:\n    pass\n\nif not has_profile:"
new = "except Exception as exc:\n    import logging; logging.warning(f'Profile check failed: {type(exc).__name__}: {exc}')\n\nif not has_profile:"
if old in content:
    content = content.replace(old, new)
    open('frontend/app.py', 'w', encoding='utf-8').write(content)
    print("FIXED: added error logging")
else:
    print("FAILED: block not found")

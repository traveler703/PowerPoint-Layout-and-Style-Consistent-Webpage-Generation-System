# Manual Test Scripts

This folder contains integration and smoke-test scripts that may call the backend API,
real LLM clients, or write generated template artifacts. They are kept under `test/`
for discoverability, but their filenames intentionally do not start with `test_` so
default `pytest` runs stay fast and deterministic.

Run examples:

```bash
python test/manual/template_generator_suite.py --quick
python test/manual/template_generator_suite.py --validate-file templates/data/ink.json
python test/manual/all_templates.py
python test/manual/ocean_theme.py
python test/manual/toy_pages.py
```

Use the scripts in this folder when you explicitly want end-to-end checks, generated
HTML/template output, or live model behavior.

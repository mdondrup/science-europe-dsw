# Science Europe DMP Template

Science Europe Generic Data Management Plan template based on the RDA DMP Common Standard (DCS).

This repository contains a DSW template that exports a Science Europe style DMP in both structured and narrative variants, as HTML and Word.

## Compatibility

- Template ID: `rda-science-europe-generic`
- Metamodel: `18.0`
- Knowledge model: `research.data.no:norway-generic` (minimum `1.2.0`)

## Export Formats

The template provides four formats:

- HTML (Science Europe) - structured
- HTML (Science Europe) - narrative
- Word (Science Europe) - structured
- Word (Science Europe) - narrative

Word exports are generated through a jinja HTML step followed by pandoc conversion to DOCX.

## Local Development

Set up the local environment:

```bash
bash tools/setup.sh
```

Render structured HTML:

```bash
.venv/bin/python tools/render.py --input input/Example-DMP.json --template "$PWD/src/science-europe-dmp.html.j2" -o out/se-structured.html
```

Render narrative HTML:

```bash
.venv/bin/python tools/render.py --input input/Example-DMP.json --template "$PWD/src/science-europe-dmp-narrative.html.j2" -o out/se-narrative.html
```

Convert structured HTML to Word:

```bash
.venv/bin/python tools/html_to_docx.py out/se-structured.html out/se-structured.docx
```

Convert narrative HTML to Word:

```bash
.venv/bin/python tools/html_to_docx.py out/se-narrative.html out/se-narrative.docx
```

Notes:

- `tools/html_to_docx.py` mirrors the template pandoc conversion step.
- A local pandoc installation is required for DOCX conversion.

## Repository Structure

- `src/science-europe-dmp.html.j2`: structured entry template
- `src/science-europe-dmp-narrative.html.j2`: narrative entry template
- `src/_se_body.html.j2`: shared Science Europe body and rendering macros
- `tools/render.py`: local template renderer
- `tools/html_to_docx.py`: local HTML to DOCX conversion helper
- `template.json`: DSW template definition and export format wiring

## Registry

This template is intended for publication through DSW Registry:

- https://registry.ds-wizard.org/templates

## License

Apache-2.0

## Contributors

- Michael Dondrup (ORCID: 0000-0002-2371-5928)

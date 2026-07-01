# Science Europe DMP (Word)

Science Europe Generic Data Management Plan template, based on the [RDA DMP Common Standard (DCS)](https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard). It produces a structured DMP document following the Science Europe DMP layout. The template is designed for use in [Data Stewardship Wizard](https://ds-wizard.org) or [FAIR Wizard](https://fair-wizard.com/) with the [Norwegian DSW Knowledge Model](https://registry.ds-wizard.org/knowledge-models/research.data.no:norway-generic:latest).

## Export formats

The template provides two export formats:

- **HTML (Science Europe)** — renders the DMP to HTML via Jinja (`src/science-europe-dmp.html.j2`).
- **Word Document (Science Europe)** — renders the same HTML and converts it to `.docx` with pandoc, using `src/reference.docx` for Word styles and `src/tables.lua` for full-width, styled tables.

It requires the `research.data.no:norway-generic` knowledge model (version 1.2.0 or higher).

## Usage

This template is available through [DSW Registry](https://registry.ds-wizard.org/templates).

This repo contains rendering tools for local development and testing. To render the template locally, you can use the `render.py` script:

```bash
.venv/bin/python tools/render.py --input input/Example-DMP.json --template "$PWD/src/science-europe-dmp.html.j2" -o out/example-science-europe-dmp.html
.venv/bin/python tools/html_to_docx.py out/example-science-europe-dmp.html out/example-science-europe-dmp.docx

## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [DHP-stottepakke/madmp-template](https://github.com/DHP-stottepakke/madmp-template), you can [report issues](https://github.com/DHP-stottepakke/madmp-template/issues) there and fork it for customisations or contributions.


## AI-Assisted Development

Some recent changes in this repository were developed with AI-assisted tooling. Proposed code, template mappings, local tooling, and documentation changes were reviewed and adapted by human contributors before being kept in the repository.

For the work captured in this thread, the following AI tooling was used:

- Agent: GitHub Copilot coding agent
- Models: Claude Opus 4.8, GPT-5.4


### Contributors

* **Michael Dondrup** <[mdondrup@gmail.com](mailto:mdondrup@gmail.com)>
  * ORCID: [0000-0002-2371-5928](https://orcid.org/0000-0002-2371-5928)
  * GitHub: [@mdondrup](https://github.com/mdondrup)


## Changelog

### 1.0.0

 - Initial release of the Horizon Europe Generic DMP template, based on the RDA DMP Common Standard. Compatible with DSW Knowledge Model `research.data.no:norway-generic` version 1.2.0 or higher. Provides HTML and Word export formats with custom styling and table formatting.
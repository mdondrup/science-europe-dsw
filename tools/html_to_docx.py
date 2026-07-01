#!/usr/bin/env python3
"""Convert a rendered HTML file to DOCX exactly like the DSW pandoc step.

This mirrors the ``pandoc`` step in template.json: it runs pandoc with the
reference document . Because all the work happens
inside pandoc, the local output is identical to what DSW produces.

Usage:
    python tools/html_to_docx.py INPUT.html OUTPUT.docx 
"""
from __future__ import annotations

import argparse

import pypandoc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_html")
    ap.add_argument("output_docx")
    args = ap.parse_args()

    pypandoc.convert_file(
        args.input_html,
        "docx",
        outputfile=args.output_docx,
        extra_args=[
        ],
    )
    print(f"wrote {args.output_docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

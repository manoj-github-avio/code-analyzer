"""
Check a PR diff for alignment with a local design document.

Usage:
    python src/design_alignment_agent.py <design-doc> <diff-file>
    cat my.diff | python src/design_alignment_agent.py <design-doc>

Example:
    python src/design_alignment_agent.py design-doc-sample.docx sample-mule-pr.diff
"""

import json
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

_ALIGNMENT_SYSTEM = """You are a software architect reviewing a PR diff for alignment with a design document.

Given a design document and a PR diff, identify:
- Where the change aligns with approved design decisions
- Where the change drifts from or contradicts the design

Return ONLY valid JSON:
{
  "drifts": [
    {
      "area": "Error Handling",
      "issue": "PR returns HTTP 503 for database connectivity errors; design mandates HTTP 500 for all runtime errors.",
      "severity": "high",
      "suggestion": "Change the on-error-continue payload to return HTTP 500, not 503."
    }
  ],
  "aligned": [
    "Correlation ID is captured from the inbound request and stored in a flow variable as required by design section 3."
  ],
  "summary": "2 drift(s) detected, 3 areas aligned with the design"
}

severity must be "high", "medium", or "low".
- high: directly contradicts an explicit design decision or introduces an out-of-scope feature
- medium: deviates from a recommended pattern but does not break a hard rule
- low: style or minor inconsistency
"""


def _read_design_doc(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Design document not found: {file_path}")
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join(p.extract_text() for p in reader.pages if p.extract_text())
    raise ValueError(f"Unsupported format '{suffix}'. Supported: .md, .txt, .docx, .pdf")


def _parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def analyze_alignment(design_doc: str, diff: str) -> dict:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=_ALIGNMENT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Design document:\n\n{design_doc}\n\n"
                    f"---\n\n"
                    f"PR diff:\n```diff\n{diff}\n```"
                ),
            }
        ],
    )
    return _parse_json(response.content[0].text)


def read_diff() -> str:
    if len(sys.argv) > 2:
        diff_path = Path(sys.argv[2])
        if not diff_path.exists():
            print(f"Error: file not found: {diff_path}", file=sys.stderr)
            sys.exit(1)
        return diff_path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: python src/design_alignment_agent.py <design-doc> [diff-file]", file=sys.stderr)
    sys.exit(1)


def display_results(results: dict) -> None:
    drifts = results.get("drifts", [])
    aligned = results.get("aligned", [])

    print(f"\n=== Design Alignment Report ===")
    print(f"Summary: {results.get('summary', '')}\n")

    if drifts:
        print("Drift issues detected:")
        for d in drifts:
            severity = d.get("severity", "medium").upper()
            print(f"  [{severity}] {d['area']}")
            print(f"          Issue:  {d['issue']}")
            if suggestion := d.get("suggestion"):
                print(f"          Fix:    {suggestion}")
            print()

    if aligned:
        print("Aligned with design:")
        for a in aligned:
            print(f"  [OK] {a}")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/design_alignment_agent.py <design-doc> [diff-file]", file=sys.stderr)
        print("       cat my.diff | python src/design_alignment_agent.py <design-doc>", file=sys.stderr)
        sys.exit(1)

    doc_path = sys.argv[1]
    diff = read_diff()

    if not diff.strip():
        print("Error: diff is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading design document: {doc_path}", file=sys.stderr)
    design_doc = _read_design_doc(doc_path)
    print(f"Analyzing alignment ({len(design_doc)} chars)...", file=sys.stderr)

    results = analyze_alignment(design_doc, diff)
    display_results(results)


if __name__ == "__main__":
    main()

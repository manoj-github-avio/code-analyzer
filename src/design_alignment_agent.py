"""
Check a PR diff for alignment with a local design document.

Usage:
    python src/design_alignment_agent.py <owner/repo> [diff-file] [design-doc-path]
    cat my.diff | python src/design_alignment_agent.py <owner/repo>

Arguments:
    owner/repo       GitHub repository (e.g. manoj-github-avio/code-analyzer)
    diff-file        Path to a .diff file (optional; reads from stdin if omitted)
    design-doc-path  Path to design doc (.docx, .md, .txt, .pdf)
                     Defaults to samples/design-doc-sample.docx

Example:
    python src/design_alignment_agent.py manoj-github-avio/code-analyzer samples/sample-mule-pr.diff
    python src/design_alignment_agent.py manoj-github-avio/code-analyzer samples/sample-mule-pr.diff my-design.docx
"""

import json
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

_ALIGNMENT_SYSTEM = """You are a software architect reviewing a PR diff for alignment with a design document.

Return ONLY valid JSON — no markdown fences:
{
  "drifts": [
    {
      "area": "Error Handling",
      "issue": "PR returns HTTP 503 for database connectivity errors; design mandates HTTP 500 for all runtime errors.",
      "severity": "high"
    }
  ],
  "summary": "2 issue(s) detected"
}

Rules:
- Only include drifts with severity "high" or "medium" — omit low severity issues.
- Do NOT include an "aligned" list.
- Do NOT include fix suggestions — only state the issue.
- severity must be "high" or "medium".
- high: directly contradicts an explicit design decision or introduces an out-of-scope feature.
- medium: deviates from a recommended pattern but does not break a hard rule.
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
    # argv[1]=repo, argv[2]=diff-file, argv[3]=design-doc
    if len(sys.argv) > 2:
        diff_path = Path(sys.argv[2])
        if not diff_path.exists():
            print(f"Error: diff file not found: {diff_path}", file=sys.stderr)
            sys.exit(1)
        return diff_path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: python src/design_alignment_agent.py <owner/repo> [diff-file] [design-doc-path]", file=sys.stderr)
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
        print("Usage: python src/design_alignment_agent.py <owner/repo> [diff-file] [design-doc-path]", file=sys.stderr)
        print("       cat my.diff | python src/design_alignment_agent.py <owner/repo>", file=sys.stderr)
        sys.exit(1)

    repo = sys.argv[1]
    doc_path = sys.argv[3] if len(sys.argv) > 3 else "samples/design-doc-sample.docx"
    diff = read_diff()

    if not diff.strip():
        print("Error: diff is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Repo:            {repo}", file=sys.stderr)
    print(f"Design document: {doc_path}", file=sys.stderr)
    design_doc = _read_design_doc(doc_path)
    print(f"Analyzing alignment ({len(design_doc)} chars)...", file=sys.stderr)

    results = analyze_alignment(design_doc, diff)
    display_results(results)


if __name__ == "__main__":
    main()

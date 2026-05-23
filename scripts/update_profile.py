#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from pathlib import Path

README_PATH = Path("README.md")

CAREER_START = date(2019, 11, 1)


def month_diff(start: date, end: date) -> tuple[int, int]:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    years, rem = divmod(months, 12)
    return years, rem


def make_header_block(today: date) -> str:
    years, months = month_diff(CAREER_START, today)
    exp_text = f"{years}y {months}m"
    return "\n".join(
        [
            "<p align=\"center\">",
            "  <strong>Python Automation Engineer | Test Automation Engineer | OpenSource Enthusiast & Contributor</strong><br>",
            "  Bengaluru, Karnataka, India | "
            f"{exp_text} experience since Nov 2019 across Server, Telecom, Internet, Entertainment, and Industrial Automation domains<br>",
            "  Last company: ABB (Relieved May 2026) | Open to Hiring: Yes (Actively Looking)",
            "</p>",
        ]
    )


def make_summary_block() -> str:
    return (
        "Test Automation Engineer focused on Python-based quality engineering with hands-on experience across "
        "server, telecom, internet, entertainment, and industrial automation domains. I work across UI/API "
        "automation, regression strategy, Linux/Windows validation, CI workflows, and cross-functional delivery. "
        "I am actively upskilling in Playwright, AI-assisted testing, LLM workflows, RAG, prompt engineering, "
        "MCP, and agentic developer tooling to deliver faster and more reliable releases."
    )


def replace_section(content: str, start: str, end: str, replacement: str) -> str:
    if start not in content or end not in content:
        raise RuntimeError(f"Missing markers: {start} / {end}")
    prefix = content.split(start, 1)[0]
    suffix = content.split(end, 1)[1]
    return f"{prefix}{start}\n{replacement}\n{end}{suffix}"


def main() -> None:
    today = date.today()
    content = README_PATH.read_text(encoding="utf-8")
    content = replace_section(
        content,
        "<!-- AUTO:HEADER:START -->",
        "<!-- AUTO:HEADER:END -->",
        make_header_block(today),
    )
    content = replace_section(
        content,
        "<!-- AUTO:SUMMARY:START -->",
        "<!-- AUTO:SUMMARY:END -->",
        make_summary_block(),
    )
    content = replace_section(
        content,
        "<!-- AUTO:FOCUS:START -->",
        "<!-- AUTO:FOCUS:END -->",
        "\n".join(
            [
                "- **Open to hiring:** Last worked at ABB (Test Automation Engineer, Bengaluru) and actively seeking new roles.",
                "- **Job search focus:** Python/Test Automation, QA Engineering, AI-assisted QA, and product quality roles across Bengaluru, remote India, and hybrid India.",
                "- **Currently learning:** Playwright, advanced API automation patterns, LLM+RAG practical workflows, and MCP-enabled agent tooling.",
                "- **Current open-source focus:** Continuing contributions to `aaif-goose/goose` and evaluating testing/automation OSS projects for future contributions.",
                "- **Planned certifications:** ISTQB, AI-for-QA, and role-relevant Python/test automation credentials.",
                "- **Outside work/hobbies:** Reading, research, learning by experimentation, and networking with people and communities.",
                f"- **Last auto-refresh date:** {today.isoformat()}",
            ]
        ),
    )
    README_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()

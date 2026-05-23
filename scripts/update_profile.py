#!/usr/bin/env python3
"""Generate the GitHub profile README and optionally sync profile metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - GitHub Actions uses modern Python.
    ZoneInfo = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "profile.json"
README_PATH = ROOT / "README.md"
TIMEZONE = "Asia/Kolkata"
USER_AGENT = "sunilkumarvalmiki-profile-sync"
ASCII_REPLACEMENTS = str.maketrans(
    {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u3002": "."
    }
)


def load_profile() -> dict[str, Any]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def today_ist() -> dt.date:
    return dt.datetime.now(ist_timezone()).date()


def ist_timezone() -> dt.tzinfo:
    if ZoneInfo is not None:
        try:
            return ZoneInfo(TIMEZONE)
        except Exception:
            pass
    return dt.timezone(dt.timedelta(hours=5, minutes=30), name="IST")


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value[:10])


def format_api_date(value: str | None) -> str:
    if not value:
        return "Unknown"
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    parsed = parsed.astimezone(ist_timezone())
    return parsed.date().isoformat()


def experience_months(start: str, today: dt.date) -> int:
    started = parse_date(start)
    months = (today.year - started.year) * 12 + today.month - started.month
    if today.day < started.day:
        months -= 1
    return max(months, 0)


def experience_label(months: int) -> str:
    years, remaining_months = divmod(months, 12)
    year_label = "year" if years == 1 else "years"
    if remaining_months == 0:
        return f"{years} {year_label}"
    month_label = "month" if remaining_months == 1 else "months"
    return f"{years} {year_label} {remaining_months} {month_label}"


def experience_short(months: int) -> str:
    years, remaining_months = divmod(months, 12)
    if remaining_months == 0:
        return f"{years}+ yrs"
    return f"{years} yrs {remaining_months} mos"


def quote_badge_part(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def badge(label: str, message: str, color: str, logo: str = "", logo_color: str = "white") -> str:
    if message == label:
        url = f"https://img.shields.io/badge/{quote_badge_part(label)}-{color}?style=for-the-badge"
    else:
        url = (
            f"https://img.shields.io/badge/{quote_badge_part(label)}-"
            f"{quote_badge_part(message)}-{color}?style=for-the-badge"
        )
    if logo:
        url += f"&logo={quote_badge_part(logo)}&logoColor={quote_badge_part(logo_color)}"
    alt_text = label if message == label else f"{label}: {message}"
    return f"![{alt_text}]({url})"


def badge_img(label: str, message: str, color: str, logo: str = "", logo_color: str = "white") -> str:
    url = (
        f"https://img.shields.io/badge/{quote_badge_part(label)}-"
        f"{quote_badge_part(message)}-{color}?style=for-the-badge"
    )
    if logo:
        url += f"&logo={quote_badge_part(logo)}&logoColor={quote_badge_part(logo_color)}"
    return f'<img alt="{escape_attr(label)}" src="{url}">'


def escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def table_cell(value: Any) -> str:
    text = ascii_text(str(value or "").replace("\n", " ").strip())
    return text.replace("|", "\\|")


def ascii_text(value: str) -> str:
    translated = value.translate(ASCII_REPLACEMENTS)
    normalized = unicodedata.normalize("NFKD", translated)
    return normalized.encode("ascii", "ignore").decode("ascii")


def api_get(url: str, token: str | None) -> Any | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"warning: GitHub API request failed for {url}: {exc}", file=sys.stderr)
        return None


def api_patch(url: str, token: str, payload: dict[str, Any]) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28"
    }
    request = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def contribution_repo(item: dict[str, Any]) -> str:
    if item.get("repo"):
        return str(item["repo"])
    repository_url = str(item.get("repository_url", ""))
    parts = repository_url.rstrip("/").split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    repository = item.get("repository") or {}
    if isinstance(repository, dict):
        return str(repository.get("full_name") or repository.get("nameWithOwner") or "")
    return ""


def fetch_contributions(profile: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    username = profile["username"]
    config = profile["open_source"]
    query = f"author:{username} is:pr is:merged"
    params = urllib.parse.urlencode(
        {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": "50"
        }
    )
    data = api_get(f"https://api.github.com/search/issues?{params}", token)
    if not data or "items" not in data:
        return list(config["fallback_contributions"])

    excluded = {repo.lower() for repo in config.get("exclude_repos", [])}
    included_own_repos = {repo.lower() for repo in config.get("include_own_repos", [])}
    owner_prefix = f"{username.lower()}/"
    contributions: list[dict[str, Any]] = []
    for item in data["items"]:
        repo = contribution_repo(item)
        if not repo or repo.lower() in excluded:
            continue
        if repo.lower().startswith(owner_prefix) and repo.lower() not in included_own_repos:
            continue
        contributions.append(
            {
                "repo": repo,
                "number": item.get("number"),
                "title": item.get("title", ""),
                "url": item.get("html_url", ""),
                "closed_at": item.get("closed_at") or item.get("updated_at")
            }
        )
        if len(contributions) >= int(config.get("max_items", 12)):
            break
    return contributions or list(config["fallback_contributions"])


def fetch_recent_repos(profile: dict[str, Any], token: str | None) -> list[dict[str, Any]]:
    username = profile["username"]
    config = profile["github_activity"]
    max_repos = int(config.get("max_repos", 8))
    repo_notes = config.get("repo_notes", {})
    url = (
        f"https://api.github.com/users/{quote_badge_part(username)}/repos"
        f"?type=owner&sort=pushed&direction=desc&per_page={max_repos}"
    )
    data = api_get(url, token)
    if not isinstance(data, list):
        return list(profile["github_activity"]["fallback_repos"])
    repos = []
    for repo in data:
        if repo.get("archived"):
            continue
        repos.append(
            {
                "full_name": repo.get("full_name", ""),
                "html_url": repo.get("html_url", ""),
                "description": repo_notes.get(repo.get("full_name", "")) or repo.get("description") or "Public repository activity.",
                "language": repo.get("language") or "",
                "pushed_at": repo.get("pushed_at"),
                "fork": bool(repo.get("fork"))
            }
        )
        if len(repos) >= max_repos:
            break
    return repos or list(profile["github_activity"]["fallback_repos"])


def render_header(profile: dict[str, Any], months: int) -> list[str]:
    hiring_message = "Yes - actively looking" if profile["open_to_hiring"] else "Not currently"
    lines = [
        f"# {profile['name']}",
        "",
        '<p align="center">',
        f"  <strong>{profile['role_headline']}</strong><br>",
        f"  {profile['employment_note']} | Available for hiring | {experience_label(months)} experience<br>",
        f"  Software engineering exposure across {', '.join(profile['domains'])}<br>",
        f"  Working from {profile['location']} | I enjoy networking, communities, research, learning, and experiments.",
        "</p>",
        "",
        '<p align="center">'
    ]
    for contact in profile["contacts"]:
        lines.extend(
            [
                f'  <a href="{contact["url"]}">',
                "    "
                + badge_img(
                    contact["badge_label"],
                    contact["badge_message"],
                    contact["color"],
                    contact.get("logo", ""),
                    contact.get("logo_color", "white")
                ),
                "  </a>"
            ]
        )
    lines.extend(
        [
            "</p>",
            "",
            '<p align="center">',
            "  "
            + badge_img(
                "Open to Hiring",
                hiring_message,
                "2E8B57" if profile["open_to_hiring"] else "59636E"
            ),
            "  " + badge_img("Last Company", profile["current_or_last_company"], "5B21B6"),
            "  " + badge_img("Experience", experience_label(months), "0E7490"),
            "  " + badge_img("Location", profile["location"], "59636E"),
            "</p>",
            ""
        ]
    )
    return lines


def render_professional_summary(profile: dict[str, Any], months: int) -> list[str]:
    summary = profile["professional_summary"]
    domains = ", ".join(profile["domains"])
    return [
        "## Professional Summary",
        "",
        (
            f"{profile['last_role']['title']} with {experience_label(months)} of experience "
            f"across SDLC and STLC, with hands-on work across {domains} domains. "
            f"{summary['skills_sentence']}"
        ),
        "",
        summary["team_sentence"],
        "",
        summary["learning_sentence"],
        ""
    ]


def render_current_focus(profile: dict[str, Any]) -> list[str]:
    last = profile["last_role"]
    search = profile["job_search"]
    return [
        "## Current Focus",
        "",
        (
            f"- **Open to hiring:** Available for hiring and actively looking for new roles. "
            f"Most recently worked at {last['company']} as a {last['title']} in {last['location']}, "
            f"focused on {last['domain']} for {last['product']}."
        ),
        (
            f"- **Job search focus:** Targeting {', '.join(search['target_roles'])} roles where I can apply "
            f"{', '.join(search['expertise'])}. Preferred locations: {', '.join(search['preferred_locations'])}."
        ),
        f"- **Domain focus:** Interested in {', '.join(search['target_domains'])}.",
        f"- **Currently learning:** {', '.join(profile['currently_learning'])}.",
        (
            "- **Current open-source focus:** Contributing to AI agent and developer-tooling projects, "
            "with recent merged work in aaif-goose/goose and openhuman."
        ),
        f"- **Planned certifications:** {', '.join(profile['planned_certifications'])}.",
        f"- **Outside work:** {', '.join(profile['outside_work'])}.",
        ""
    ]


def render_skills(profile: dict[str, Any]) -> list[str]:
    lines = ["## Core Skills", ""]
    for category in profile["skills"]:
        lines.extend([f"### {category['category']}", ""])
        badges = [
            badge(label, label, color, logo, logo_color)
            for label, color, logo, logo_color in category["items"]
        ]
        lines.extend(badges)
        lines.append("")
    return lines


def render_open_source(profile: dict[str, Any], contributions: list[dict[str, Any]]) -> list[str]:
    notes = profile["open_source"].get("project_notes", {})
    lines = [
        "## Open Source Contributions",
        "",
        (
            "Verified public merged pull requests authored by "
            f"[{profile['username']}](https://github.com/{profile['username']}), refreshed daily with GitHub Actions."
        ),
        "",
        "| Merged | Project | Contribution | Area |",
        "| --- | --- | --- | --- |"
    ]
    for item in contributions:
        repo = contribution_repo(item)
        title = table_cell(item.get("title", "Merged pull request"))
        number = item.get("number")
        url = item.get("url", "")
        pr_text = f"[#{number}]({url}) - {title}" if number and url else title
        project = f"[{repo}](https://github.com/{repo})" if repo else "Unknown"
        area = notes.get(repo, "Open-source project contribution.")
        lines.append(
            f"| {format_api_date(item.get('closed_at'))} | {project} | {pr_text} | {table_cell(area)} |"
        )
    lines.extend(["", "### Looking To Contribute Next", ""])
    lines.extend([f"- {item}" for item in profile["open_source"].get("future_focus", [])])
    lines.append("")
    return lines


def render_team_value() -> list[str]:
    return [
        "## What I Bring To Teams",
        "",
        "- Maintainable automation suites for UI, API, regression, functional, and production-support testing.",
        "- Strong QA engineering across test planning, test scripts, test data, defect triage, documentation, and release confidence.",
        "- Practical debugging across web applications, APIs, Linux, Windows, Docker, MQTT, SSH, Salesforce, and connected systems.",
        "- Experience across server, telecom, internet, entertainment, and industrial automation environments.",
        "- A collaborative approach with developers, QA engineers, product owners, support engineers, business stakeholders, and communities.",
        "- Open-source contribution discipline: small reproducible fixes, focused validation, clear documentation, and steady follow-through.",
        ""
    ]


def render_github_activity(profile: dict[str, Any], repos: list[dict[str, Any]], generated_on: dt.date) -> list[str]:
    lines = [
        "## GitHub Activity",
        "",
        f"Daily activity snapshot generated on {generated_on.isoformat()} from public GitHub repository data.",
        "",
        "| Repository | Latest Push | Language | Scope | Notes |",
        "| --- | --- | --- | --- | --- |"
    ]
    for repo in repos:
        full_name = repo.get("full_name", "")
        repo_link = f"[{full_name}]({repo.get('html_url', '')})" if repo.get("html_url") else table_cell(full_name)
        scope = "Fork / contribution lane" if repo.get("fork") else "Owned"
        lines.append(
            f"| {repo_link} | {format_api_date(repo.get('pushed_at'))} | "
            f"{table_cell(repo.get('language') or 'Mixed')} | {scope} | {table_cell(repo.get('description'))} |"
        )
    lines.append("")
    return lines


def render_stats(profile: dict[str, Any]) -> list[str]:
    username = profile["username"]
    return [
        "## Stats",
        "",
        '<p align="center">',
        (
            f'  <img alt="Profile visits" '
            f'src="https://komarev.com/ghpvc/?username={username}&label=PROFILE%20VISITS&color=0e75b6&style=for-the-badge">'
        ),
        "</p>",
        "",
        '<p align="center">',
        (
            f'  <img alt="Sunil Kumar GitHub profile details" '
            f'src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username={username}&theme=github_dark">'
        ),
        "</p>",
        "",
        '<p align="center">',
        (
            f'  <img height="180" alt="Sunil Kumar GitHub stats" '
            f'src="https://github-profile-summary-cards.vercel.app/api/cards/stats?username={username}&theme=github_dark">'
        ),
        (
            f'  <img height="180" alt="Sunil Kumar productive time" '
            f'src="https://github-profile-summary-cards.vercel.app/api/cards/productive-time?username={username}&theme=github_dark&utcOffset=5.5">'
        ),
        "</p>",
        "",
        '<p align="center">',
        (
            f'  <img height="180" alt="Sunil Kumar repositories by language" '
            f'src="https://github-profile-summary-cards.vercel.app/api/cards/repos-per-language?username={username}&theme=github_dark">'
        ),
        (
            f'  <img height="180" alt="Sunil Kumar most committed languages" '
            f'src="https://github-profile-summary-cards.vercel.app/api/cards/most-commit-language?username={username}&theme=github_dark">'
        ),
        "</p>",
        "",
        '<p align="center">',
        (
            f'  <img alt="Sunil Kumar GitHub streak" '
            f'src="https://streak-stats.demolab.com?user={username}&theme=tokyonight&hide_border=true">'
        ),
        "</p>",
        ""
    ]


def render_readme(profile: dict[str, Any], token: str | None) -> str:
    generated_on = today_ist()
    months = experience_months(profile["career_start"], generated_on)
    contributions = fetch_contributions(profile, token)
    repos = fetch_recent_repos(profile, token)
    lines: list[str] = []
    lines.extend(render_header(profile, months))
    lines.extend(render_professional_summary(profile, months))
    lines.extend(render_current_focus(profile))
    lines.extend(render_skills(profile))
    lines.extend(render_open_source(profile, contributions))
    lines.extend(render_team_value())
    lines.extend(render_github_activity(profile, repos, generated_on))
    lines.extend(render_stats(profile))
    lines.extend(
        [
            "<!--",
            "This README is generated by scripts/update_profile.py.",
            "Edit data/profile.json first, then run: python scripts/update_profile.py",
            "-->",
            ""
        ]
    )
    return "\n".join(lines)


def sync_github_profile(profile: dict[str, Any], token: str, months: int) -> None:
    profile_config = profile["github_profile"]
    bio = profile_config["bio_template"].format(
        experience_short=experience_short(months),
        experience=experience_label(months)
    )
    payload = {
        "name": profile_config.get("name", profile["display_name"]),
        "bio": bio[:160],
        "company": profile_config.get("company", profile["current_or_last_company"]),
        "blog": profile_config.get("blog", ""),
        "location": profile["location"],
        "hireable": bool(profile["open_to_hiring"])
    }
    status, body = api_patch("https://api.github.com/user", token, payload)
    if status < 200 or status >= 300:
        raise SystemExit(f"GitHub profile sync failed with HTTP {status}: {body}")
    print("Synced GitHub profile metadata.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if README.md is not up to date")
    parser.add_argument("--skip-readme", action="store_true", help="skip README generation")
    parser.add_argument("--sync-github-profile", action="store_true", help="sync GitHub user bio/company/location")
    args = parser.parse_args()

    profile = load_profile()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    if not args.skip_readme:
        rendered = render_readme(profile, token)
        current = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""
        if args.check:
            if current != rendered:
                print("README.md is not up to date. Run: python scripts/update_profile.py", file=sys.stderr)
                return 1
            print("README.md is up to date.")
        elif current != rendered:
            README_PATH.write_text(rendered, encoding="utf-8", newline="\n")
            print("Updated README.md.")
        else:
            print("README.md already up to date.")

    if args.sync_github_profile:
        profile_token = os.environ.get("GH_PROFILE_TOKEN")
        if not profile_token:
            raise SystemExit("GH_PROFILE_TOKEN is required to update GitHub profile metadata.")
        months = experience_months(profile["career_start"], today_ist())
        sync_github_profile(profile, profile_token, months)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

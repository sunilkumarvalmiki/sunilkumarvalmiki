# Profile Automation

This repository updates the public GitHub profile from `data/profile.json`.

## Daily Update

`.github/workflows/profile-sync.yml` runs every day at 06:00 Asia/Kolkata and can also be started manually from GitHub Actions.

The workflow:

1. Runs `python scripts/update_profile.py`.
2. Recalculates work experience from `2019-11-01`.
3. Refreshes merged public pull requests authored by `sunilkumarvalmiki`.
4. Refreshes recent public GitHub repository activity.
5. Commits `README.md` only when generated content changes.

## Updating Profile Content

Edit `data/profile.json` first, then run:

```powershell
python scripts/update_profile.py
python scripts/update_profile.py --check
```

## GitHub Profile Bio Sync

GitHub Actions can update the README with the built-in `GITHUB_TOKEN`.

Updating the actual GitHub account bio, company, location, portfolio, and hiring flag requires a repository secret named `GH_PROFILE_TOKEN`. That token must be allowed to update the authenticated user's profile. When the secret is present, the same daily workflow runs:

```powershell
python scripts/update_profile.py --skip-readme --sync-github-profile
```

If the secret is not present, the workflow still updates the profile README and logs that metadata sync was skipped.

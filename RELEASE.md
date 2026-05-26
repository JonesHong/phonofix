# Release SOP — phonofix

## Pre-release Checklist

- [ ] All CI checks green on `main`
- [ ] Perf regression gate green (`.github/workflows/perf.yml`)
- [ ] CHANGELOG.md + CHANGELOG.zh-TW.md updated with new section
- [ ] Version bumped: `pyproject.toml` + `src/phonofix/__init__.py:__version__`
- [ ] MIGRATION.md updated if breaking changes
- [ ] SPEC.md unchanged (or version bumped if v0.5+)
- [ ] LICENSE / SECURITY / CONTRIBUTING reviewed

## Release Steps

```bash
# 1. Bump version (edit pyproject.toml + __init__.py + CHANGELOG)
# 2. PR + merge to main
git switch main
git pull
# 3. Tag
git tag v0.4.0
git push origin v0.4.0
# 4. GitHub Actions automatic build (cibuildwheel) + PyPI OIDC publish
# 5. Verify
curl -s https://pypi.org/pypi/phonofix/json | jq -r .info.version  # 應為 0.4.0
# 6. GitHub Release auto-created with CHANGELOG section
```

## Trusted Publisher (PyPI OIDC) Setup（一次性）

1. 到 https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher:
   - PyPI Project Name: `phonofix`
   - Owner: `JonesHong`
   - Repository: `phonofix`
   - Workflow name: `release.yml`
   - Environment: `pypi`
3. 完成後 `.github/workflows/release.yml` push tag 即自動 publish，無需 API token

## Hotfix Release

對 v0.4.x 線上 critical bug:

```bash
git switch -c hotfix/v0.4.1 v0.4.0
# fix + test
git tag v0.4.1
git push origin v0.4.1
```

## License Compatibility Audit (release 前必跑)

```bash
~/workshop/lab/phonofix/.venv/bin/python -m pip licenses 2>/dev/null || \
  uv run pip-licenses --format=markdown --with-urls
# 確認所有 dep 與 MIT 相容（GPL/AGPL transitive 要警示）
# phonemizer is BSD-3，但 espeak-ng 是 GPL — 用 subprocess 不靜態連結 → MIT compatible
```

## Post-release

- [ ] Verify pip install in fresh venv
- [ ] Update memory note / blog post
- [ ] Close milestone, open next minor

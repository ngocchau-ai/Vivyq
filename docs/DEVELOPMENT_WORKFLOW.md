# Development Workflow

**Branches**

- `main` — releasable tip (force-pushed once with `ffad2d1` after user confirmation).
- `develop` — integration branch for ongoing work; open PRs `develop` → `main`.

**Data files**

- `data/e0_benchmark/*.npy` stay on disk for local tests but are **not** in Git
  (GitHub 100 MB limit; `train_latents.npy` is ~109 MB).
- Integrity is tracked by `data/e0_benchmark/checksums.sha256`.
- Regenerate with `scripts/generate_dataset.py` if missing.

**Build / test**

```powershell
./scripts/build_core.ps1
$env:PYTHONPATH='D:\Vivyqu\python'
python -m pytest tests -q
```

**Changelog**

- 2026-09-29 | MiMoCode | Create develop workflow doc for PR develop→main.

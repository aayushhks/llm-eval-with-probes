# Working in this repo

## Git conventions

**Always commit directly to `main`.** Do not create feature branches. If a
session starts on some other branch, switch back to `main` first.

**Commit one file per commit**, with a single-line message describing that
file's change — no body, no bullet lists.

**Always commit with `--no-verify`** (skips the pre-commit hooks).

**Never sign commits.** Some environments set `commit.gpgsign true` with their
own signing key; a commit signed by a key that isn't the author's shows up as
**Unverified** on GitHub. Disable signing explicitly rather than relying on the
ambient config.

**Author every commit as the repo owner:**

```bash
git -c user.name=aayushhks -c user.email=aayushhks03@gmail.com \
    -c commit.gpgsign=false commit --no-verify -m "message"
```

**Never add trailers** — no `Co-Authored-By`, no `Generated with`, no session
links. Match the existing history: lowercase, imperative, short.

```
add github actions eval gate workflow
make mlx optional dependency for linux deploys
fix vercel spa routing for refresh and direct urls
```

## Project notes

- The MLX probes are **Apple Silicon only** and import lazily, so the backend
  runs fine on Linux — evals there just need `--no-probes`.
- Migrations use `JSONB`; **Postgres is required**, SQLite will not work for
  deployment even though the tests use it.
- `backend/app/core/config.py` and `backend/app/datasets/loader.py` resolve
  paths via `parents[3]`, so the `backend/` directory has to stay one level
  below the repo root — including inside Docker images.
- Deployment lives in `deploy/DEPLOY.md` (AWS EC2 + Docker).

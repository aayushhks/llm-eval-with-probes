# Deploying to AWS (EC2 + Docker)

The whole stack runs on one EC2 instance: Postgres, the FastAPI backend, and
Caddy serving the built React dashboard and reverse-proxying the API. Caddy and
the app share an origin, so the frontend's default `/api` base URL works with no
CORS involved and no `VITE_*` variable to set.

```
             :80/:443
                │
          ┌─────▼─────┐
          │   Caddy   │   /api/* ──► backend:8000   (prefix stripped)
          │  (web)    │   /*     ──► /srv           (static React build)
          └─────┬─────┘
                │  docker network (nothing else published)
       ┌────────▼────────┐        ┌──────────┐
       │ backend (uvicorn)│───────►│ db (pg16)│
       └──────────────────┘        └──────────┘
```

**What does not run here:** the MLX probes are Apple Silicon only. You keep
training and running those on your Mac; this deployment hosts the dashboard and
the results database. Getting your local results onto it is [step 5](#5-load-your-eval-data).

## Cost

Inside the 12-month free tier this is **$0**: `t3.micro` covers 750 h/month
(i.e. one instance running continuously), 30 GB of EBS, and 100 GB/month of
outbound transfer. After the 12 months it lands around **$10/month**
(~$7.50 instance + ~$2.40 storage).

Allocate an **Elastic IP** and attach it to the instance — free while attached
to a running instance, and it keeps your address stable across stop/start.

---

## 1. Launch the instance

EC2 → **Launch instance**:

| Field | Value |
|---|---|
| AMI | **Amazon Linux 2023** |
| Instance type | **t3.micro** (free tier; use `t2.micro` if your region's free tier lists that instead) |
| Key pair | Create one, download the `.pem`, `chmod 400 it.pem` |
| Storage | **30 GB gp3** (the free-tier maximum) |
| Advanced details → User data | paste the contents of [`deploy/user-data.sh`](user-data.sh) |

The user-data script installs Docker + Compose, adds a 2 GB swap file, and
clones the repo to `/home/ec2-user/llm-eval-with-probes`. The swap matters:
`t3.micro` has 1 GB of RAM and the Vite build will OOM without it.

It deliberately does **not** start the stack — `.env` has to be filled in first.

## 2. Security group

| Type | Port | Source |
|---|---|---|
| SSH | 22 | **My IP** |
| HTTP | 80 | Anywhere (`0.0.0.0/0`) |
| HTTPS | 443 | Anywhere (`0.0.0.0/0`) — only needed once you add a domain |

Do not open 5432. Postgres has no published port; it is reachable only from
inside the Docker network, and [step 5](#5-load-your-eval-data) tunnels over SSH.

## 3. Configure

Give user-data a minute or two to finish, then:

```bash
ssh -i it.pem ec2-user@<ELASTIC_IP>
cd llm-eval-with-probes

cp .env.prod.example .env
openssl rand -base64 32          # paste as POSTGRES_PASSWORD
vi .env
```

At minimum set `POSTGRES_PASSWORD`. Leave `SITE_ADDRESS=:80` for now; the API
keys are only needed if you want to run evals on the server itself.

## 4. Start

```bash
docker compose -f docker-compose.prod.yaml up -d --build
```

First build takes ~5 minutes. The backend applies `alembic upgrade head` on every
start — safe to re-run, it no-ops when the schema is current.

```bash
docker compose -f docker-compose.prod.yaml ps
curl localhost/api/health          # {"status":"ok"}
curl localhost/api/health/ready    # {"status":"ready"} — confirms Postgres
```

Open `http://<ELASTIC_IP>`. The dashboard loads with an empty run list, which is
what step 5 fixes.

> If `docker compose` says permission denied, your shell predates the docker
> group change from user-data — `exit` and SSH back in.

## 5. Load your eval data

Your runs (with the probe scores) live in your Mac's Postgres. The schema is
already migrated on the server, so a data-only dump is all you need.

**On your Mac**, with the local DB up:

```bash
pg_dump -h localhost -p 5432 -U eval -d eval \
    --data-only --no-owner --no-privileges \
    -t eval_runs -t eval_cases -t eval_traces > eval-data.sql

scp -i it.pem eval-data.sql ec2-user@<ELASTIC_IP>:~/
```

**On the server:**

```bash
cd llm-eval-with-probes
docker compose -f docker-compose.prod.yaml exec -T db \
    psql -U eval -d eval < ~/eval-data.sql
```

Refresh the dashboard — the runs are there.

Re-loading the same dump later will collide on primary keys. To replace
everything instead of appending:

```bash
docker compose -f docker-compose.prod.yaml exec -T db \
    psql -U eval -d eval -c \
    "TRUNCATE eval_traces, eval_cases, eval_runs CASCADE;"
```

You can also generate fresh runs on the server, though without probe scores —
they are the interesting half of the dashboard, so prefer the dump above:

```bash
docker compose -f docker-compose.prod.yaml exec backend \
    python /srv/scripts/run_eval.py --prompt v1 --no-probes
```

## 6. Add a domain and HTTPS (optional)

Point an `A` record at the Elastic IP, then on the server:

```bash
vi .env      # SITE_ADDRESS=eval.yourdomain.com   (bare hostname, no https://)
docker compose -f docker-compose.prod.yaml up -d
```

Caddy provisions and renews the certificate automatically. Port 443 must be open
and DNS must already resolve, or the ACME challenge fails.

---

## Operations

```bash
CF="-f docker-compose.prod.yaml"

docker compose $CF logs -f backend      # tail logs (also: web, db)
docker compose $CF ps                   # status
docker compose $CF restart backend      # restart one service
docker compose $CF down                 # stop (data survives in volumes)
```

**Deploy a change:**

```bash
git pull && docker compose $CF up -d --build
```

**Back up the database:**

```bash
docker compose $CF exec -T db pg_dump -U eval -d eval > backup-$(date +%F).sql
```

Worth doing before any `down -v` — that flag deletes the volumes and your runs
with them.

## Troubleshooting

**Build killed / exit 137** — out of memory. Confirm swap is on (`free -h` should
show 2 GB); if user-data didn't run, create it manually:

```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Backend restarting** — `docker compose $CF logs backend`. Usually a
`POSTGRES_PASSWORD` that changed after the volume was initialised; the old
password persists in the volume. Either restore the original value or reset with
`down -v` (destroys data).

**502 from Caddy** — the backend is still starting or unhealthy. Check
`docker compose $CF ps` and the backend logs.

**Dashboard loads but shows no runs** — expected until step 5. Verify the API
directly with `curl localhost/api/runs`.

**Certificate won't issue** — DNS must resolve to the Elastic IP *before* Caddy
requests one, port 443 must be open, and `SITE_ADDRESS` must be a bare hostname.
`docker compose $CF logs web` shows the ACME error.

---
name: dockerize
description: Add Docker to an existing project — generate a multi-stage production-ready Dockerfile, a .dockerignore tuned to the project type, and an optional docker-compose.yml with auto-detected services (Postgres for Django/Rails, Redis for cache-using Node, etc.). Use when the user says "/dockerize", "přidej Docker", "udělej mi Dockerfile", "containerize this project", "add docker-compose", or otherwise wants to add Docker artifacts to a project.
---

# dockerize — procedure

Add Docker to an existing project. Multi-stage Dockerfile, project-type-aware `.dockerignore`, optional `docker-compose.yml` with detected services. Never overwrite existing files; if any of `Dockerfile`/`docker-compose.yml`/`.dockerignore` exists, ask before doing anything to them.

## 1. Survey

- `pwd` to confirm the target directory.
- `ls -la` to see what's already there (especially the four files this skill touches).
- Note which of these exist: `Dockerfile`, `docker-compose.yml` / `docker-compose.yaml` / `compose.yaml`, `.dockerignore`.
- Read `.gitignore` if it exists — it's a useful starting point for `.dockerignore`.

## 2. Detect project type

Match the marker files in the root (same set as `project-init`):

| Marker | Type | Default base image (runtime) | Default port |
|---|---|---|---|
| `package.json` | Node.js | `node:lts-alpine` | 3000 |
| `pyproject.toml`, `setup.py`, `requirements*.txt`, `Pipfile` | Python | `python:3.12-slim` | 8000 |
| `go.mod` | Go | `gcr.io/distroless/static-debian12` or `alpine:3` | 8080 |
| `Cargo.toml` | Rust | `debian:bookworm-slim` | 8080 |
| `composer.json` | PHP | `php:8.3-fpm-alpine` | 9000 |
| `pom.xml`, `build.gradle*` | Java/JVM | `eclipse-temurin:21-jre` | 8080 |
| `Gemfile` | Ruby | `ruby:3.3-slim` | 3000 |
| `mix.exs` | Elixir | `elixir:1.16-alpine` | 4000 |
| `*.csproj`, `*.sln` | .NET | `mcr.microsoft.com/dotnet/aspnet:8.0` | 8080 |

If you can read the language version from the project (e.g. `package.json#engines.node`, `pyproject.toml#requires-python`, `go.mod#go`), pin the base image to that version instead of the default.

If you find multiple markers (e.g. a polyglot repo), ask the user which one to dockerize.

If you find none, ask the user to specify the type (or stop with a helpful message).

## 3. Detect framework and likely services

Beyond the type, look for framework hints that determine compose services:

| Hint | Framework | Suggested services |
|---|---|---|
| `next.config.*`, `next` in `package.json` deps | Next.js | (optional) Postgres + Redis |
| `nuxt.config.*`, `nuxt` in deps | Nuxt | (optional) Postgres |
| `manage.py` + `django` in deps | Django | Postgres + Redis (channels/cache) |
| `Rakefile` + `rails` in `Gemfile` | Rails | Postgres + Redis |
| `flask` / `fastapi` / `uvicorn` in deps | Flask/FastAPI | (optional) Postgres |
| `nestjs`, `express`, `fastify` in deps | Node web API | (optional) Postgres |
| `pom.xml` with `spring-boot-starter-web` | Spring Boot | Postgres |
| `laravel` in `composer.json` | Laravel | MariaDB + Redis |
| `phoenix` in `mix.exs` | Phoenix | Postgres |

Skip compose entirely for CLIs, libraries, and pure scripts (no `bin`/`server`/`web` entry point and no framework hint).

## 4. Detect port

Order of preference:
1. `EXPOSE` already in a comment somewhere, or a `PORT` env var in `.env*`.
2. Framework defaults (Django 8000, Rails 3000, Flask 5000, Express 3000, …).
3. Read explicit `app.listen(N)` / `port = N` if obvious from `src/`.
4. The default-port column in the type table above.

## 5. Generate the Dockerfile

Multi-stage: `builder` for dependency install / compile / asset build, `runtime` for the tiny image that ships. Always end the runtime stage with a non-root user. Use type-appropriate templates — pick from the catalog below.

**Node.js (TypeScript or JS, with `npm`/`pnpm`/`yarn`):**

```dockerfile
# syntax=docker/dockerfile:1.7
ARG NODE_VERSION=lts-alpine

FROM node:${NODE_VERSION} AS builder
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN if [ -f pnpm-lock.yaml ]; then corepack enable && pnpm install --frozen-lockfile; \
    elif [ -f yarn.lock ]; then corepack enable && yarn install --immutable; \
    else npm ci; fi
COPY . .
RUN npm run build --if-present

FROM node:${NODE_VERSION} AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S app && adduser -S app -G app
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/package.json ./
USER app
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

(Adjust `dist/`, `CMD`, and the `EXPOSE` port to what the project actually produces.)

**Python (with `pyproject.toml` + uv/pip):**

```dockerfile
# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION} AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY pyproject.toml requirements*.txt ./
RUN pip install --prefix=/install -r requirements.txt 2>/dev/null || pip install --prefix=/install .

FROM python:${PYTHON_VERSION} AS runtime
WORKDIR /app
RUN useradd --create-home --shell /bin/false app
COPY --from=builder /install /usr/local
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["python", "-m", "app"]
```

**Go (CGO_DISABLED, distroless runtime):**

```dockerfile
# syntax=docker/dockerfile:1.7
ARG GO_VERSION=1.22

FROM golang:${GO_VERSION}-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/app ./...

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /out/app /app
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/app"]
```

**Rust (musl static binary, distroless or scratch runtime):**

```dockerfile
# syntax=docker/dockerfile:1.7
FROM rust:1.79-alpine AS builder
RUN apk add --no-cache musl-dev
WORKDIR /src
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release --target x86_64-unknown-linux-musl

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /src/target/x86_64-unknown-linux-musl/release/app /app
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/app"]
```

**JVM (Spring Boot, layered jar):**

```dockerfile
# syntax=docker/dockerfile:1.7
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /src
COPY . .
RUN ./mvnw -B -DskipTests package || ./gradlew -x test bootJar

FROM eclipse-temurin:21-jre
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder --chown=app:app /src/target/*.jar /app/app.jar
COPY --from=builder --chown=app:app /src/build/libs/*.jar /app/app.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

For other types (PHP, Ruby, Elixir, .NET) write an analogous two-stage Dockerfile. Always: pinned base image, dependency layer separate from source layer (so rebuilds are fast), non-root `USER`, only the runtime artifacts in the final stage, an `EXPOSE` matching the detected port.

After writing the Dockerfile, show the user a `head -20` preview and ask via `AskUserQuestion` whether to keep it or adjust the base image / port / start command.

## 6. Generate `.dockerignore`

Always include:

```
.git
.gitignore
.DS_Store
._*
.idea/
.vscode/
*.md
node_modules/   # if Node
.venv/          # if Python
__pycache__/    # if Python
target/         # if Rust/JVM/.NET
build/          # if Gradle/Cargo/etc.
dist/           # if Node
*.log
.env*
docker-compose*.yml
Dockerfile*
```

Trim entries that don't apply to the detected type. The goal is a small build context: anything that isn't needed inside the image (tests are often *not* needed if they aren't run during build, but if `RUN npm test` etc. happens in `builder`, keep them).

If `.dockerignore` already exists, append only the lines that aren't already there.

## 7. Optionally generate `docker-compose.yml`

Ask via `AskUserQuestion`:

- `Generate docker-compose.yml with detected services (<list>)` (recommended if framework hints found services)
- `Generate docker-compose.yml with just the app (no extra services)`
- `Skip — Dockerfile only`

If `docker-compose.yml` already exists, ask whether to merge in (offering a separate file `docker-compose.dockerize.yml` for the user to splice manually) or skip.

Template (adapt to detected services):

```yaml
services:
  app:
    build: .
    ports:
      - "<port>:<port>"
    environment:
      - DATABASE_URL=postgres://app:app@db:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    develop:
      watch:
        - action: sync
          path: .
          target: /app
          ignore:
            - node_modules/

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  db-data:
  redis-data:
```

Drop services the user didn't pick. Drop their env vars from `app.environment`. Drop their `depends_on` entries.

Tell the user the default credentials are `app/app/app` and they should change them for anything not local.

## 8. Final summary

Tell the user:
- Which files were created (or skipped because they already existed)
- The detected type, framework (if any), services, and port
- A one-liner to test: `docker build -t <project-name> .` and (if compose) `docker compose up`
- Any TODOs left in the templates the user needs to fill in (e.g. real `CMD`, real `DATABASE_URL`)

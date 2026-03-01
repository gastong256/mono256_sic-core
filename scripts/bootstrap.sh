#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SENTINEL=".initialized"

if [[ -f "$SENTINEL" ]]; then
    echo "Repository already initialized. Delete '$SENTINEL' to re-run bootstrap."
    exit 0
fi

# ── Collect values ────────────────────────────────────────────────────────────
# Accept values from env vars (for CI/non-interactive use) or prompt.

ask() {
    local var_name="$1"
    local prompt="$2"
    local default="${3:-}"

    if [[ -n "${!var_name:-}" ]]; then
        echo "  $prompt: ${!var_name} (from env)"
        return
    fi

    if [[ -n "$default" ]]; then
        read -rp "  $prompt [$default]: " value
        printf -v "$var_name" '%s' "${value:-$default}"
    else
        while [[ -z "${!var_name:-}" ]]; do
            read -rp "  $prompt: " value
            printf -v "$var_name" '%s' "$value"
        done
    fi
}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Django DRF Template — Bootstrap Init   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

ask PROJECT_NAME   "Project name (e.g. Acme API)"
ask PROJECT_SLUG   "Python package slug (e.g. acme_api)"
ask SERVICE_NAME   "Docker service name (e.g. acme-api)"
ask OWNER          "Owner / team"
ask DESCRIPTION    "Short description"
ask PORT           "Port" "8000"

# Validate slug: only lowercase letters, digits, underscores
if ! echo "$PROJECT_SLUG" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "ERROR: PROJECT_SLUG must be lowercase letters, digits, and underscores only."
    exit 1
fi

# ── Generate secret key ───────────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
    DJANGO_SECRET_KEY="$(python3 -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#\$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(50)))
")"
else
    DJANGO_SECRET_KEY="$(head -c 50 /dev/urandom | base64 | tr -d '\n/+=' | head -c 50)"
fi

echo ""
echo "Replacing placeholders..."

# Files to process (exclude binary, git, .venv, node_modules)
INCLUDE_PATTERNS=(
    "*.py" "*.toml" "*.yml" "*.yaml" "*.md" "*.json" "*.sh"
    "*.txt" "*.cfg" "*.ini" "*.env" "*.example" "Makefile" "Dockerfile"
)

EXCLUDE_DIRS=(".git" ".venv" "node_modules" "__pycache__" "*.egg-info" "htmlcov")

build_find_args() {
    local args=()
    for d in "${EXCLUDE_DIRS[@]}"; do
        args+=(-not -path "*/$d/*" -not -path "*/$d")
    done
    echo "${args[@]}"
}

replace_in_files() {
    local placeholder="$1"
    local value="$2"

    # Escape for sed
    local escaped_value
    escaped_value="$(printf '%s\n' "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')"

    for pattern in "${INCLUDE_PATTERNS[@]}"; do
        # shellcheck disable=SC2046
        find . $(build_find_args) -type f -name "$pattern" \
            -exec grep -lF "$placeholder" {} \; \
            | while IFS= read -r file; do
                sed -i "s|${placeholder}|${escaped_value}|g" "$file"
                echo "  patched: $file"
            done
    done
}

replace_in_files "__PROJECT_NAME__"      "$PROJECT_NAME"
replace_in_files "__PROJECT_SLUG__"      "$PROJECT_SLUG"
replace_in_files "__SERVICE_NAME__"      "$SERVICE_NAME"
replace_in_files "__OWNER__"             "$OWNER"
replace_in_files "__DESCRIPTION__"       "$DESCRIPTION"
replace_in_files "__PORT__"              "$PORT"
replace_in_files "__DJANGO_SECRET_KEY__" "$DJANGO_SECRET_KEY"

# ── Rename postman files ──────────────────────────────────────────────────────
if ls postman/__PROJECT_SLUG__*.json &>/dev/null 2>&1; then
    :  # Already replaced above — nothing to rename
fi

# Rename any remaining __PROJECT_SLUG__ in filenames
find postman/ -name "*__PROJECT_SLUG__*" | while IFS= read -r f; do
    new_name="${f//__PROJECT_SLUG__/$PROJECT_SLUG}"
    mv "$f" "$new_name"
    echo "  renamed: $f → $new_name"
done

# ── Create .env from .env.example ─────────────────────────────────────────────
if [[ ! -f .env ]]; then
    cp .env.example .env
    # Patch the generated secret key directly into .env
    sed -i "s|__DJANGO_SECRET_KEY__|${DJANGO_SECRET_KEY}|g" .env
    echo "Created .env from .env.example"
fi

# ── Install deps ──────────────────────────────────────────────────────────────
echo ""
echo "Installing dependencies..."
if command -v uv &>/dev/null; then
    uv sync
else
    echo "WARNING: uv not found. Install uv and run 'uv sync' manually."
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# ── Install pre-commit hooks ──────────────────────────────────────────────────
if command -v uv &>/dev/null; then
    echo "Installing pre-commit hooks..."
    uv run pre-commit install
fi

# ── Stamp sentinel ────────────────────────────────────────────────────────────
echo "__PROJECT_SLUG__" > "$SENTINEL"
echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SENTINEL"

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next steps:"
echo "  docker compose up -d postgres"
echo "  make migrate"
echo "  make run"

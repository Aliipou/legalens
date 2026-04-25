#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:?Usage: restore.sh <backup_file.sql.gz>}"
DB_HOST="${PGHOST:-db}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-legalens}"
DB_USER="${PGUSER:-legalens}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restoring from ${BACKUP_FILE} → ${DB_NAME}"
echo "WARNING: This will drop and recreate all tables. Press Ctrl+C within 5s to abort."
sleep 5

PGPASSWORD="${PGPASSWORD:-}" psql \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

gunzip -c "$BACKUP_FILE" | PGPASSWORD="${PGPASSWORD:-}" psql \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restore complete."

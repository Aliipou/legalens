#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_HOST="${PGHOST:-db}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-legalens}"
DB_USER="${PGUSER:-legalens}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/legalens_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting backup → ${BACKUP_FILE}"

PGPASSWORD="${PGPASSWORD:-}" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-password \
  --format=plain \
  --compress=9 \
  | gzip > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete: ${BACKUP_FILE} (${SIZE})"

# Upload to S3/Azure if configured
if [ -n "${AWS_S3_BUCKET:-}" ]; then
  aws s3 cp "$BACKUP_FILE" "s3://${AWS_S3_BUCKET}/backups/$(basename "$BACKUP_FILE")"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Uploaded to s3://${AWS_S3_BUCKET}"
fi

if [ -n "${AZURE_STORAGE_ACCOUNT:-}" ]; then
  az storage blob upload \
    --account-name "$AZURE_STORAGE_ACCOUNT" \
    --container-name "${AZURE_CONTAINER:-legalens-backups}" \
    --name "backups/$(basename "$BACKUP_FILE")" \
    --file "$BACKUP_FILE"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Uploaded to Azure Blob Storage"
fi

# Prune old backups
find "$BACKUP_DIR" -name "legalens_*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete
REMAINING=$(find "$BACKUP_DIR" -name "legalens_*.sql.gz" | wc -l)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Pruned backups older than ${RETENTION_DAYS}d. Remaining: ${REMAINING}"

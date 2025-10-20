#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-/var/backups/taskmate}
RETENTION_DAYS=${RETENTION_DAYS:-7}
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILENAME="taskmate_${TIMESTAMP}.sql.gz"
TARGET_DIR="${BACKUP_DIR%/}"
mkdir -p "$TARGET_DIR"

if [[ -z "${POSTGRES_DSN:-}" ]]; then
  echo "POSTGRES_DSN environment variable must be set" >&2
  exit 1
fi

pg_dump --dbname="$POSTGRES_DSN" | gzip >"$TARGET_DIR/$FILENAME"

find "$TARGET_DIR" -type f -name 'taskmate_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

echo "Backup written to $TARGET_DIR/$FILENAME"

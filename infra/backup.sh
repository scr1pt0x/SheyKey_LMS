#!/bin/bash
# Daily PostgreSQL backup to MinIO
# Add to crontab: 0 2 * * * /srv/lms/infra/backup.sh

set -euo pipefail

source /srv/lms/.env.prod

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/lms_backup_${TIMESTAMP}.sql.gz"
BUCKET="lms"
OBJECT_KEY="backups/lms_backup_${TIMESTAMP}.sql.gz"
RETAIN_DAYS=30

# Create dump
docker compose -f /srv/lms/infra/docker-compose.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"

# Upload to MinIO via mc
docker run --rm --network lms_lms_net \
  -v "${BACKUP_FILE}:/backup.sql.gz:ro" \
  minio/mc:latest \
  sh -c "mc alias set minio http://lms_minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} && \
         mc cp /backup.sql.gz minio/${BUCKET}/${OBJECT_KEY}"

echo "Backup uploaded to MinIO: ${OBJECT_KEY}"

# Cleanup local file
rm "${BACKUP_FILE}"

# Remove backups older than RETAIN_DAYS from MinIO
CUTOFF_DATE=$(date -d "-${RETAIN_DAYS} days" +%Y%m%d 2>/dev/null || date -v-"${RETAIN_DAYS}"d +%Y%m%d)
docker run --rm --network lms_lms_net \
  minio/mc:latest \
  sh -c "mc alias set minio http://lms_minio:9000 ${MINIO_ACCESS_KEY} ${MINIO_SECRET_KEY} && \
         mc ls minio/${BUCKET}/backups/ | grep 'lms_backup' | while read -r line; do
           fname=\$(echo \$line | awk '{print \$NF}');
           fdate=\$(echo \$fname | grep -o '[0-9]\{8\}');
           if [ \"\$fdate\" '<' \"${CUTOFF_DATE}\" ]; then
             mc rm \"minio/${BUCKET}/backups/\$fname\";
             echo \"Deleted old backup: \$fname\";
           fi
         done"

echo "Backup process complete at $(date)"

#!/bin/bash
set -e

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/tmp/backups"
mkdir -p "$BACKUP_DIR"

echo "[$DATE] Starting database backups..."

# 1. Finans DB Backup
echo "Dumping finans_db..."
PGPASSWORD=$FINANS_DB_PASSWORD pg_dump -h finans-postgres-service -U $FINANS_DB_USER $FINANS_DB_NAME > "$BACKUP_DIR/finans_db_$DATE.sql"

# 2. Mooddiary DB Backup
echo "Dumping mooddiary_db..."
PGPASSWORD=$MOODDIARY_DB_PASSWORD pg_dump -h mooddiary-db-service -U $MOODDIARY_DB_USER $MOODDIARY_DB_NAME > "$BACKUP_DIR/mooddiary_db_$DATE.sql"

# 3. Compress
echo "Compressing backups..."
cd /tmp
tar -czvf "vps_databases_$DATE.tar.gz" -C "$BACKUP_DIR" .

# 4. Upload to Google Drive using rclone
echo "Uploading to Google Drive..."
# The rclone.conf is mounted at /root/.config/rclone/rclone.conf
rclone copy "vps_databases_$DATE.tar.gz" grive:/VPS_Backups/

echo "[$DATE] Backup completed successfully!"

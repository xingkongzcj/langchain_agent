#!/usr/bin/env bash
# 智学助手备份：MySQL 逻辑备份 + Chroma 向量库打包
# 部署位置：/usr/local/bin/studymate-backup.sh
# 依赖：docker、/opt/studymate/.env（读 MYSQL_PASSWORD / MYSQL_DATABASE）
set -euo pipefail

REMOTE_DIR="${STUDYMATE_DIR:-/opt/studymate}"
BACKUP_DIR="$REMOTE_DIR/backups"
KEEP_DAYS="${KEEP_DAYS:-7}"

mkdir -p "$BACKUP_DIR"

DB_PASS="$(grep -E '^MYSQL_PASSWORD=' "$REMOTE_DIR/.env" | cut -d= -f2-)"
DB_NAME="$(grep -E '^MYSQL_DATABASE=' "$REMOTE_DIR/.env" | cut -d= -f2- || true)"
DB_NAME="${DB_NAME:-study_mate}"

STAMP="$(date +%Y%m%d-%H%M%S)"

# 1) MySQL：--single-transaction 保证一致性，不锁表
docker exec study_mate_mysql \
  mysqldump -uroot -p"$DB_PASS" --single-transaction --quick --default-character-set=utf8mb4 "$DB_NAME" \
  | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"

# 2) Chroma 向量库（在应用容器里，直接打成 tar 流）
docker exec study_mate_app tar czf - -C /data chroma \
  > "$BACKUP_DIR/chroma-$STAMP.tar.gz"

# 3) 清理过期备份
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'chroma-*.tar.gz' -mtime +"$KEEP_DAYS" -delete

echo "backup ok: db-$STAMP.sql.gz $(du -h "$BACKUP_DIR/db-$STAMP.sql.gz" | cut -f1), chroma-$STAMP.tar.gz $(du -h "$BACKUP_DIR/chroma-$STAMP.tar.gz" | cut -f1)"

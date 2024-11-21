#!/bin/bash

# 设置备份目录
BACKUP_DIR="backups"
BACKUP_NAME="data_backup_$(date +%Y%m%d_%H%M%S).tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 停止应用（可选，确保数据一致性）
docker-compose stop

# 备份 volume
docker run --rm \
    -v diary-streamlit_streamlit_data:/data \
    -v $(pwd)/$BACKUP_DIR:/backup \
    ubuntu tar czf /backup/$BACKUP_NAME /data

# 重启应用（如果之前停止了）
docker-compose start

# 保留最近 7 天的备份
find $BACKUP_DIR -name "data_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_NAME" 
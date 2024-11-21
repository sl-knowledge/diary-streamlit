#!/bin/bash

echo "Docker Cleanup Script"
echo "-------------------"

# 显示当前状态
echo "Current Docker status:"
docker system df

# 确认是否继续
read -p "Do you want to continue with cleanup? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Operation cancelled"
    exit 1
fi

# 删除悬空镜像
echo "Removing dangling images..."
dangling_images=$(docker images -f "dangling=true" -q)
if [ -n "$dangling_images" ]; then
    docker rmi $dangling_images
    echo "Dangling images removed"
else
    echo "No dangling images found"
fi

# 显示清理后的状态
echo -e "\nNew Docker status:"
docker system df 
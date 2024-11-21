"""生成模拟数据"""
import sqlite3
import json
from datetime import datetime, timedelta
import random
import os
from pathlib import Path
import logging
import sys
from config import Config

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def ensure_data_dir():
    """确保数据目录存在并有正确权限"""
    try:
        # 使用绝对路径
        base_dir = Path(__file__).parent.parent
        data_dir = base_dir / 'data'
        data_dir.mkdir(exist_ok=True)
        
        db_path = data_dir / 'diary.db'
        if not db_path.exists():
            # 创建空数据库文件
            db_path.touch()
            
        logger.debug(f"Data directory created/verified: {data_dir.absolute()}")
        logger.debug(f"Database path: {db_path.absolute()}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create/verify data directory: {e}", exc_info=True)
        return False

def init_database():
    """初始化数据库"""
    try:
        base_dir = Path(__file__).parent.parent
        db_path = base_dir / 'data/diary.db'
        
        # 如果数据库文件已存在，先删除它以确保完全重新初始化
        if db_path.exists():
            db_path.unlink()
        
        logger.debug(f"Attempting to connect to database at: {db_path}")
        
        db = sqlite3.connect(str(db_path))
        db.execute("PRAGMA foreign_keys = ON")
        
        # 确保创建所有必要的列
        db.executescript('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                mood TEXT,
                weather TEXT,
                location TEXT,
                attachments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS entry_tags (
                entry_id TEXT,
                tag_id TEXT,
                PRIMARY KEY (entry_id, tag_id),
                FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                entry_id TEXT,
                topic TEXT,
                keywords TEXT,
                sentiment REAL,
                FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
            );
        ''')
        
        db.commit()
        logger.debug("Database initialized successfully")
        return db
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        return None

def generate_mock_data():
    """生成模拟数据"""
    try:
        config = Config()
        logger.debug("Starting mock data generation...")
        
        # 1. 确保数据目录存在
        if not ensure_data_dir():
            logger.error("Failed to create/verify data directory")
            return False
            
        # 2. 初始化数据库（创建表结构）
        if not init_database():
            logger.error("Failed to initialize database")
            return False
            
        # 3. 连接数据库
        db_path = config.DB_PATH
        logger.debug(f"Connecting to database at: {db_path}")
        db = sqlite3.connect(str(db_path))
        
        # 4. 验证表是否存在
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='topics'")
        if not cursor.fetchone():
            logger.error("Required tables do not exist")
            return False
            
        # 5. 清空现有数据
        logger.debug("Clearing existing data...")
        db.executescript('''
            DELETE FROM topics;
            DELETE FROM entry_tags;
            DELETE FROM tags;
            DELETE FROM entries;
        ''')
        
        # 模拟数据
        moods = ['开心', '平静', '疲惫', '兴奋', '焦虑', '伤心']
        weathers = ['晴朗', '多云', '小雨', '阴天', '大晴天']
        locations = ['家里', '公司', '咖啡馆', '图书馆', '公园']
        
        # 模拟日记内容模板
        templates = [
            "今天{mood}。{weather}的天气让我{feeling}。{activity}",
            "在{location}度过了充实的一天。{weather}，心情{mood}。{thought}",
            "{weather}的早晨，来到{location}。{activity}让我感到{mood}。",
            "这是{mood}的一天。{activity}时想到了很多。{thought}"
        ]
        
        activities = [
            "看完了一本很棒的书",
            "和朋友聊了很久",
            "完成了一个重要项目",
            "学习了新技能",
            "整理了房间",
            "写了一篇博客",
            "做了美味的晚餐",
            "晨跑五公里"
        ]
        
        thoughts = [
            "生活真美好。",
            "要继续努力。",
            "希望明天会更好。",
            "感恩当下的一切。",
            "需要调整心态。",
            "保持乐观很重要。",
            "珍惜身边的人。",
            "坚持就是胜利。"
        ]
        
        feelings = [
            "很放松",
            "充满干劲",
            "有点感动",
            "特别满足",
            "略显疲惫",
            "很有期待",
            "有些感慨"
        ]
        
        # 生成过去30天的日记
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for i in range(31):
            current_date = start_date + timedelta(days=i)
            # 使用标准日期格式 YYYY-MM-DD
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 随机决定是否写日记（80%的概率）
            if random.random() < 0.8:
                # 可能一天写多篇（20%的概率）
                entries_count = 2 if random.random() < 0.2 else 1
                
                for _ in range(entries_count):
                    mood = random.choice(moods)
                    weather = random.choice(weathers)
                    location = random.choice(locations)
                    activity = random.choice(activities)
                    thought = random.choice(thoughts)
                    feeling = random.choice(feelings)
                    
                    # 生成内容
                    template = random.choice(templates)
                    content = template.format(
                        mood=mood,
                        weather=weather,
                        location=location,
                        activity=activity,
                        thought=thought,
                        feeling=feeling
                    )
                    
                    # 生成标题
                    title = f"{activity[:10]}..."
                    
                    # 插入日记时使用标准格式日期
                    db.execute('''
                        INSERT INTO entries (
                            id, date, title, content, mood, weather, location,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        f"entry_{date_str}_{_}",
                        date_str,
                        title,
                        content,
                        mood,
                        weather,
                        location,
                        current_date.strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    # 生成主题分析
                    sentiment = random.uniform(-1, 1)
                    keywords = random.sample([
                        '生活', '工作', '学习', '家庭', '健康', 
                        '娱乐', '运动', '阅读', '写作', '思考'
                    ], 3)
                    
                    db.execute('''
                        INSERT INTO topics (
                            id, entry_id, topic, keywords, sentiment
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        f"topic_{date_str}_{_}",
                        f"entry_{date_str}_{_}",
                        random.choice(['日常', '工作', '学习', '生活感悟']),
                        json.dumps(keywords, ensure_ascii=False),
                        sentiment
                    ))
        
        # 提交更改
        db.commit()
        logger.info("Mock data generated successfully")
        
        # 6. 验证数据生成
        if not verify_mock_data():
            logger.error("Data verification failed")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error generating mock data: {e}", exc_info=True)
        return False
    finally:
        if 'db' in locals():
            db.close()

def verify_mock_data():
    """验证模拟数据是否成功生成"""
    try:
        db = sqlite3.connect('data/diary.db')
        cursor = db.cursor()
        
        # 检查entries表
        cursor.execute("SELECT COUNT(*) FROM entries")
        entries_count = cursor.fetchone()[0]
        
        # 检查topics表
        cursor.execute("SELECT COUNT(*) FROM topics")
        topics_count = cursor.fetchone()[0]
        
        # 获取日期范围
        cursor.execute("SELECT MIN(date), MAX(date) FROM entries")
        date_range = cursor.fetchone()
        
        print(f"""
模拟数据验证结果:
- 日记总数: {entries_count}
- 主题分析数: {topics_count}
- 日期范围: {date_range[0]} 到 {date_range[1]}
        """)
        
        # 获取一条示例数据
        cursor.execute("""
            SELECT e.date, e.title, e.content, e.mood, t.topic, t.sentiment 
            FROM entries e 
            LEFT JOIN topics t ON e.id = t.entry_id 
            LIMIT 1
        """)
        sample = cursor.fetchone()
        if sample:
            print(f"""
示例数据:
日期: {sample[0]}
标题: {sample[1]}
内容: {sample[2]}
心情: {sample[3]}
主题: {sample[4]}
情感值: {sample[5]}
            """)
            
        db.close()
        return entries_count > 0
        
    except Exception as e:
        print(f"验证数据时出错: {e}")
        return False

if __name__ == "__main__":
    print("开始生成模拟数据...")
    if generate_mock_data():
        print("模拟数据生成成功！")
        verify_mock_data()
    else:
        print("模拟数据生成失败！请检查日志获取详细信息。") 
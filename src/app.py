import streamlit as st
import sqlite3
from datetime import datetime
import json
from pathlib import Path
import uuid
import shutil
import logging
import os
from config import Config
from i18n.manager import t, I18nManager
from streamlit_timeline import timeline
from annotated_text import annotated_text

# 设置 watchdog 的日志级别为 WARNING，减少调试输出
logging.getLogger('watchdog').setLevel(logging.WARNING)

# 保持我们应用的日志级别不变
logging.basicConfig(level=logging.DEBUG if Config.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

# 使用 Config 类的属性
config = Config()
ALLOWED_EXTENSIONS = config.APP_CONFIG['allowed_extensions']

def init_db():
    """Initialize database connection"""
    try:
        config = Config()
        db = sqlite3.connect(str(config.DB_PATH))
        db.execute("PRAGMA foreign_keys = ON")
        return db
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def init_directories():
    """Initialize required directories"""
    Path("data").mkdir(exist_ok=True)
    config.UPLOAD_DIR.mkdir(exist_ok=True)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return the path"""
    if uploaded_file is None:
        return None
        
    # Create unique filename
    file_extension = Path(uploaded_file.name).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        st.error(f"Unsupported file type: {file_extension}")
        return None
        
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = config.UPLOAD_DIR / unique_filename
    
    # Save the file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)
        
    return str(file_path.relative_to(Path("data")))

def save_entry(title, content, uploaded_files, tags=None, mood=None, weather=None, location=None):
    """Save entry with attachments and tags"""
    db = init_db()
    entry_id = str(uuid.uuid4())
    
    try:
        # Save uploaded files
        attachment_paths = []
        if uploaded_files:
            for file in uploaded_files:
                path = save_uploaded_file(file)
                if path:
                    attachment_paths.append(path)
        
        # Save entry to database
        db.execute('''
            INSERT INTO entries (id, date, title, content, attachments, mood, weather, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry_id,
            datetime.now().strftime('%Y-%m-%d'),
            title,
            content,
            json.dumps(attachment_paths),
            mood,
            weather,
            location
        ))
        
        # Save tags
        if tags:
            for tag in tags:
                # First, ensure the tag exists in the tags table
                db.execute('INSERT OR IGNORE INTO tags (id, name) VALUES (?, ?)', 
                         (str(uuid.uuid4()), tag))
                
                # Get the tag_id
                cursor = db.execute('SELECT id FROM tags WHERE name = ?', (tag,))
                tag_id = cursor.fetchone()[0]
                
                # Link the tag to the entry
                db.execute('''
                    INSERT INTO entry_tags (entry_id, tag_id)
                    VALUES (?, ?)
                ''', (entry_id, tag_id))
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error saving entry: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_app():
    """Initialize application directories and database"""
    try:
        # 使用 Config 实例的属性
        config.DATA_DIR.mkdir(exist_ok=True)
        config.UPLOAD_DIR.mkdir(exist_ok=True)
        
        # Initialize database and create tables first
        db = init_db()
        if db:
            # Create tables if they don't exist
            db.executescript('''
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    attachments TEXT,
                    mood TEXT,
                    weather TEXT,
                    location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Now check if we need to generate mock data
            cursor = db.execute("SELECT COUNT(*) FROM entries")
            count = cursor.fetchone()[0]
            if count == 0:
                # No data exists, generate mock data
                from mock_data import generate_mock_data
                generate_mock_data()
                logger.info("Generated mock data")
            db.close()
        
        return True
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        return False

def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("""
            <style>
                .stTextInput > div > div > input {
                    width: 300px;
                }
                div[data-testid="stVerticalBlock"] > div:has(div.stTextInput) {
                    display: flex;
                    justify-content: center;
                    margin-top: 100px;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center;'>日记本</h1>", unsafe_allow_html=True)
        st.text_input(
            "请输入访问密钥",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    return True

def main():
    st.set_page_config(page_title=t('app.title'), layout="wide")
    
    # Add password check before showing content
    if not check_password():
        return
    
    # 添加语言切换器到右上角
    with st.container():
        col1, col2 = st.columns([6, 1])
        with col2:
            current_lang = st.selectbox(
                t('app.language'),
                ['中文', 'English'],
                index=0 if I18nManager.get_current_lang() == 'zh' else 1,
                key='lang_selector'
            )
            # 根据选择更新语言
            new_lang = 'zh' if current_lang == '中文' else 'en'
            if new_lang != I18nManager.get_current_lang():
                I18nManager.set_language(new_lang)
                st.rerun()  # 重新加载页面以应用新语言
    
    # Initialize app first
    if not init_app():
        st.error(t('error.init_failed'))
        return
        
    # Continue with normal flow
    page = st.sidebar.radio(t('nav.title'), [
        t('nav.timeline'),
        t('nav.new_entry'),
        t('nav.web_clipper')
    ])
    
    if page == t('nav.timeline'):
        show_timeline()
    elif page == t('nav.new_entry'):
        show_editor()
    else:
        show_clipper()

def show_timeline():
    st.title(t('timeline.title'))
    
    # Get the date range from database
    db = init_db()
    if db:
        try:
            cursor = db.execute("""
                SELECT MIN(date), MAX(date) 
                FROM entries
            """)
            min_date, max_date = cursor.fetchone()
            min_date = datetime.strptime(min_date, '%Y-%m-%d').date() if min_date else datetime.now().date()
            max_date = datetime.strptime(max_date, '%Y-%m-%d').date() if max_date else datetime.now().date()
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            min_date = max_date = datetime.now().date()
        finally:
            db.close()
    else:
        min_date = max_date = datetime.now().date()
    
    # 侧边栏过滤器
    with st.sidebar:
        st.subheader(t('timeline.filters'))
        filter_type = st.selectbox(
            t('timeline.filter_by'),
            [
                t('timeline.date_range'),
                t('timeline.tags'),
                t('timeline.topics'),
                t('timeline.mood'),
                t('timeline.search')
            ]
        )
        
        if filter_type == t('timeline.date_range'):
            start_date = st.date_input(
                t('timeline.start_date'),
                value=min_date,  # Set default to earliest entry
                min_value=min_date,  # Limit range to actual data
                max_value=max_date
            )
            end_date = st.date_input(
                t('timeline.end_date'),
                value=max_date,  # Set default to latest entry
                min_value=min_date,
                max_value=max_date
            )
        elif filter_type == t('timeline.tags'):
            tags = get_all_tags()
            selected_tags = st.multiselect(t('timeline.select_tags'), tags)
        elif filter_type == t('timeline.search'):
            search_query = st.text_input(t('timeline.search_placeholder'))
    
    # 主要内容区域
    tab1, tab2, tab3 = st.tabs([
        t('tabs.timeline'),
        t('tabs.insights'),
        t('tabs.analysis')
    ])
    
    with tab1:
        show_filtered_entries(filter_type, locals())
        
    with tab2:
        show_insights()
        
    with tab3:
        show_analysis()

def show_insights():
    """Display insights from journal entries"""
    st.subheader(t('insights.title'))
    
    # Get the date range from database
    db = init_db()
    if db:
        try:
            cursor = db.execute("""
                SELECT MIN(date), MAX(date) 
                FROM entries
            """)
            min_date, max_date = cursor.fetchone()
            min_date = datetime.strptime(min_date, '%Y-%m-%d').date() if min_date else datetime.now().date()
            max_date = datetime.strptime(max_date, '%Y-%m-%d').date() if max_date else datetime.now().date()
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            min_date = max_date = datetime.now().date()
        finally:
            db.close()
    else:
        min_date = max_date = datetime.now().date()
    
    # 时间范围选择 - 使用数据库中的最早日期作为默认值
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            t('insights.period_start'),
            value=min_date,  # Set default to earliest entry
            min_value=min_date,  # Limit range to actual data
            max_value=max_date,
            key='insights_start_date'
        )
    with col2:
        end_date = st.date_input(
            t('insights.period_end'),
            value=max_date,  # Set default to latest entry
            min_value=min_date,
            max_value=max_date,
            key='insights_end_date'
        )
    
    if start_date and end_date:
        if start_date > end_date:
            st.error(t('insights.date_range_error'))
            return
            
        # 1. 情绪分析区域
        st.markdown(f"### {t('insights.mood_analysis')}")
        col1, col2 = st.columns(2)
        with col1:
            show_mood_trends(start_date, end_date)
        with col2:
            show_mood_distribution(start_date, end_date)
        
        # 2. 写作习惯分析
        st.markdown(f"### {t('insights.writing_habits')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            # 写作频率统计
            show_writing_frequency(start_date, end_date)
        with col2:
            # 每篇日记字数统计
            show_word_count_stats(start_date, end_date)
        with col3:
            # 写作时间分布
            show_writing_time_distribution(start_date, end_date)
            
        # 3. 主题分析
        st.markdown(f"### {t('insights.topic_analysis')}")
        col1, col2 = st.columns(2)
        with col1:
            # 常见主题词云
            show_topic_wordcloud(start_date, end_date)
        with col2:
            # 主题变化趋势
            show_topic_trends(start_date, end_date)
            
        # 4. 重要事件时间线
        st.markdown(f"### {t('insights.key_events')}")
        show_key_events_timeline(start_date, end_date)
        
        # 5. 个人成长追踪
        st.markdown(f"### {t('insights.personal_growth')}")
        show_growth_indicators(start_date, end_date)

def show_mood_trends(start_date, end_date):
    """显示情绪趋势分析"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        # Query data
        query = """
            SELECT date, mood, COUNT(*) as count
            FROM entries
            WHERE date BETWEEN ? AND ?
                AND mood IS NOT NULL
            GROUP BY date, mood
            ORDER BY date
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_mood_data'))
            return
            
        # Use pyecharts
        from pyecharts import options as opts
        from pyecharts.charts import Line
        from streamlit_echarts import st_pyecharts
        
        # Prepare data
        dates = sorted(list(set(row[0] for row in data)))
        moods = sorted(list(set(row[1] for row in data)))
        
        # Create line chart
        line = Line()
        line.add_xaxis(dates)
        
        # Color mapping
        colors = ['#FF9800', '#4CAF50', '#9E9E9E', '#F44336', '#673AB7', '#2196F3']
        
        for idx, mood in enumerate(moods):
            y_data = []
            for date in dates:
                count = 0
                for row in data:
                    if row[0] == date and row[1] == mood:
                        count = row[2]
                        break
                y_data.append(count)
            
            line.add_yaxis(
                series_name=mood,
                y_axis=y_data,
                symbol_size=8,
                itemstyle_opts=opts.ItemStyleOpts(color=colors[idx % len(colors)]),
                label_opts=opts.LabelOpts(is_show=False),
            )
        
        line.set_global_opts(
            title_opts=opts.TitleOpts(
                title="情绪变化趋势",
                subtitle=f"从 {start_date} 到 {end_date}",
                title_textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                name="日期",
                name_location="end",
                axislabel_opts=opts.LabelOpts(rotate=45),
            ),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                name="次数",
                name_location="end",
            ),
            legend_opts=opts.LegendOpts(
                pos_top="5%",
                pos_left="center",
                orient="horizontal",
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
        
        # Display chart
        st_pyecharts(line)
        
    except Exception as e:
        logger.error(f"Error showing mood trends: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_writing_frequency(start_date, end_date):
    """显示写作频率分析"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT date, COUNT(*) as entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_entries'))
            return
            
        from pyecharts import options as opts
        from pyecharts.charts import Bar
        from streamlit_echarts import st_pyecharts
        
        dates, counts = zip(*data)
        
        bar = Bar()
        bar.add_xaxis(dates)
        bar.add_yaxis(
            "日记数量",
            counts,
            itemstyle_opts=opts.ItemStyleOpts(color='#1976D2'),
            label_opts=opts.LabelOpts(is_show=False),
        )
        
        bar.set_global_opts(
            title_opts=opts.TitleOpts(
                title="写作频率统计",
                subtitle=f"从 {start_date} 到 {end_date}",
                title_textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                name="日期",
                name_location="end",
                axislabel_opts=opts.LabelOpts(rotate=45),
            ),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                name="日记数量",
                name_location="end",
                min_=0,
                max_=max(counts) + 1,
                interval=1,
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
        )
        
        st_pyecharts(bar)
        
    except Exception as e:
        logger.error(f"Error showing writing frequency: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_analysis():
    """Display detailed analysis of journal entries"""
    st.subheader(t('analysis.title'))
    
    st.markdown(f"### {t('analysis.topic_evolution')}")
    st.markdown(f"### {t('analysis.writing_patterns')}")

def show_editor():
    st.title(t('editor.title'))
    
    # Basic editor
    title = st.text_input(t('editor.entry_title'))
    content = st.text_area(t('editor.content'), height=300)
    
    # Add mood, weather, and location selectors
    col1, col2, col3 = st.columns(3)
    with col1:
        mood = st.selectbox(
            "心情",
            ['开���', '平静', '疲惫', '兴奋', '焦虑', '伤心'],
            index=None,
            placeholder="选择心情..."
        )
    with col2:
        weather = st.selectbox(
            "天气",
            ['晴朗', '多云', '小雨', '阴天', '大晴天'],
            index=None,
            placeholder="选择天气..."
        )
    with col3:
        location = st.selectbox(
            "位置",
            ['家里', '公司', '咖啡馆', '图书馆', '公园'],
            index=None,
            placeholder="选择位置..."
        )
    
    # Tags input
    # Get existing tags for autocomplete
    existing_tags = get_all_tags()
    
    # Allow multiple tag selection with autocomplete
    selected_tags = st.multiselect(
        "标签",
        options=existing_tags,
        placeholder="选择或输入新标签...",
        help="可以选择已有标签或输入新标签，多个标签用逗号分隔"
    )
    
    # Additional free-form tags input
    new_tags = st.text_input(
        "新标签",
        placeholder="输入新标签，多个标签用逗号分隔",
        help="输入新标签，用逗号分隔多个标签"
    )
    
    # Attachments with preview
    uploaded_files = st.file_uploader(
        t('editor.add_images'), 
        accept_multiple_files=True,
        type=list(ext.replace('.', '') for ext in ALLOWED_EXTENSIONS)
    )
    
    # Preview uploaded images
    if uploaded_files:
        cols = st.columns(4)
        for idx, file in enumerate(uploaded_files):
            with cols[idx % 4]:
                st.image(file, use_column_width=True)
    
    if st.button(t('editor.save')):
        if not title:
            st.error(t('editor.title_required'))
            return
            
        # Process tags
        all_tags = set(selected_tags)
        if new_tags:
            # Split new tags by comma and strip whitespace
            new_tag_list = [tag.strip() for tag in new_tags.split(',') if tag.strip()]
            all_tags.update(new_tag_list)
            
        save_entry(title, content, uploaded_files, list(all_tags), mood, weather, location)
        st.success(t('editor.save_success'))

def show_clipper():
    st.title(t('clipper.title'))
    url = st.text_input(t('clipper.url_input'))
    if url:
        st.info(t('clipper.coming_soon'))

def get_entries_by_date(selected_date):
    """Get entries for a specific date"""
    logger.debug(f"Fetching entries for date: {selected_date}")
    
    db = init_db()
    if not db:
        logger.error("Failed to initialize database")
        return []
        
    try:
        date_str = selected_date.strftime('%Y-%m-%d')
        logger.debug(f"Formatted date: {date_str}")
        
        # 添加数据库连验证
        logger.debug("Testing database connection...")
        test_cursor = db.execute("SELECT 1")
        test_cursor.fetchone()
        logger.debug("Database connection successful")
        
        # 检查表是否存在
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        if not cursor.fetchone():
            logger.error("Table 'entries' does not exist")
            return []
            
        # 检查是否有数据
        cursor = db.execute('SELECT COUNT(*) FROM entries')
        count = cursor.fetchone()[0]
        logger.debug(f"Total entries in database: {count}")
        
        # 执行原始查询
        cursor = db.execute('''
            SELECT id, date, title, content, attachments
            FROM entries
            WHERE date = ?
            ORDER BY date DESC
        ''', (date_str,))
        
        entries = [dict(zip(['id', 'date', 'title', 'content', 'attachments'], row))
                  for row in cursor.fetchall()]
        
        logger.debug(f"Found {len(entries)} entries for date {date_str}")
        db.close()
        return entries
        
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}", exc_info=True)
        st.error("Failed to fetch entries")
        if db:
            db.close()
        return []

def show_filtered_entries(filter_type, local_vars):
    """Display filtered entries in timeline format"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        # 构建基础查询
        query = """
            SELECT e.date, e.title, e.content, e.mood, e.weather, e.location,
                   GROUP_CONCAT(DISTINCT t.name) as tags,
                   tp.keywords, tp.sentiment
            FROM entries e
            LEFT JOIN entry_tags et ON e.id = et.entry_id
            LEFT JOIN tags t ON et.tag_id = t.id
            LEFT JOIN topics tp ON e.id = tp.entry_id
        """
        
        # 添加过滤条件
        conditions = []
        params = []
        
        if filter_type == t('timeline.date_range'):
            if 'start_date' in local_vars and 'end_date' in local_vars:
                conditions.append("e.date BETWEEN ? AND ?")
                params.extend([local_vars['start_date'], local_vars['end_date']])
        elif filter_type == t('timeline.tags'):
            if 'selected_tags' in local_vars and local_vars['selected_tags']:
                placeholders = ','.join(['?' for _ in local_vars['selected_tags']])
                conditions.append(f"t.name IN ({placeholders})")
                params.extend(local_vars['selected_tags'])
        elif filter_type == t('timeline.search'):
            if 'search_query' in local_vars and local_vars['search_query']:
                search_term = f"%{local_vars['search_query']}%"
                conditions.append("""
                    (e.title LIKE ? OR 
                     e.content LIKE ? OR 
                     e.mood LIKE ? OR 
                     e.weather LIKE ? OR 
                     e.location LIKE ? OR 
                     t.name LIKE ?)
                """)
                params.extend([search_term] * 6)  # Add search term for each field
                
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " GROUP BY e.id ORDER BY e.date DESC"
        
        cursor = db.execute(query, params)
        entries = cursor.fetchall()
        
        # Show result count based on filter type
        if filter_type == t('timeline.search') and 'search_query' in local_vars and local_vars['search_query']:
            if entries:
                st.success(f"找到 {len(entries)} 条相关日记")
            else:
                st.info("未找到相关日记")
                return
        elif filter_type == t('timeline.tags') and 'selected_tags' in local_vars and local_vars['selected_tags']:
            if entries:
                st.success(f"找到 {len(entries)} 条带有所选标签的日记")
            else:
                st.info("未找到带有所选标签的日记")
                return
        elif not entries:
            st.info(t('timeline.no_entries'))
            return
            
        # 更新中文日期格式映射
        zh_months = {
            '1': '一月', '2': '二月', '3': '三月', '4': '四月',
            '5': '五月', '6': '六月', '7': '七月', '8': '八月',
            '9': '九月', '10': '十月', '11': '十一月', '12': '十二月'
        }
        
        zh_weekdays = {
            '0': '周日', '1': '周一', '2': '周二', '3': '周三',
            '4': '周四', '5': '周五', '6': '周六'
        }
        
        timeline_items = []
        for entry in entries:
            date, title, content, mood, weather, location, tags, keywords, sentiment = entry
            date_parts = date.split('-')
            
            # 转换为中文日期格式
            dt = datetime.strptime(date, '%Y-%m-%d')
            weekday = dt.strftime('%w')  # 0 is Sunday, 6 is Saturday
            chinese_date = f"{zh_months[str(int(date_parts[1]))]} {int(date_parts[2])}日 {zh_weekdays[weekday]}"
            
            # 根据是否是周末设置不同的背景颜色
            is_weekend = weekday in ['0', '6']
            background_color = '#fff5f5' if is_weekend else '#ffffff'  # 周末使用浅红色背景
            border_color = '#ffebee' if is_weekend else '#e0e0e0'     # 周末使用红色边框
            
            # 在标题中添加中文日期，周末使用不同样式
            title_html = f'''
                <div style="
                    font-size: 12px;
                    font-weight: 500;
                    color: {('#d32f2f' if is_weekend else '#1a237e')};
                    margin-bottom: 4px;
                    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei';
                    text-shadow: none;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                ">{title}</div>
                <div style="
                    font-size: 11px;  # Slightly increased from 10px
                    color: {('#e57373' if is_weekend else '#666')};
                    margin: 6px 0;    # Added more vertical margin
                    padding: 2px 0;   # Added padding
                    border-bottom: 1px solid #eee;  # Added separator
                    line-height: 1.4; # Added line height
                ">{chinese_date}</div>
            '''
            
            # 内容区域使用较大的字体，但保持其他元素小巧
            content_html = f'''
                <div style="
                    color: #333;
                    font-size: 14px;  # Increased back to 14px for better readability
                    line-height: 1.5;  # Slightly increased for better readability
                    margin: 6px 0;
                    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei';
                    text-shadow: none;
                    display: -webkit-box;
                    -webkit-line-clamp: 3;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                    background-color: #fafafa;  # Light background to distinguish content
                    padding: 8px;
                    border-radius: 4px;
                ">{content}</div>
            '''
            
            # Keep meta info and tags small
            meta_info = []
            if mood:
                meta_info.append(f'<span style="background-color: #ffcdd2; padding: 1px 4px; border-radius: 4px; font-size: 10px; margin-right: 4px;">{mood}</span>')
            if weather:
                meta_info.append(f'<span style="background-color: #b3e5fc; padding: 1px 4px; border-radius: 4px; font-size: 10px; margin-right: 4px;">{weather}</span>')
            if location:
                meta_info.append(f'<span style="background-color: #c8e6c9; padding: 1px 4px; border-radius: 4px; font-size: 10px; margin-right: 4px;">{location}</span>')
            
            meta_html = '<div style="margin: 4px 0;">' + ''.join(meta_info) + '</div>'
            
            # 标签使用更紧凑的样式
            tags_html = ''
            if tags:
                tag_list = tags.split(',')
                tags_html = ''.join([
                    f'''<span style="
                        display: inline-block;
                        padding: 1px 6px;
                        margin: 1px;
                        border-radius: 8px;
                        background-color: #e3f2fd;
                        color: #1565c0;
                        font-size: 10px;
                    ">{tag.strip()}</span>'''
                    for tag in tag_list
                ])
            
            item = {
                "start_date": {
                    "year": date_parts[0],
                    "month": date_parts[1],
                    "day": date_parts[2]
                },
                "text": {
                    "headline": title_html,
                    "text": f'''
                        <div style="
                            background-color: {background_color};
                            padding: 8px;
                            border-radius: 6px;
                            border: 1px solid {border_color};
                            font-size: 12px;
                            max-height: 200px;
                            overflow: hidden;
                        ">
                            {meta_html}
                            {content_html}
                            <div style="margin-top: 4px;">
                                {tags_html}
                            </div>
                        </div>
                    '''
                }
            }
            timeline_items.append(item)
        
        # Create timeline configuration before using it
        timeline_config = {
            "title": {
                "text": {
                    "headline": f'<h1 style="color:#1a237e; font-size:20px;">{t("timeline.title")}</h1>',
                    "text": f'<p style="color:#666; font-size:14px;">{t("timeline.subtitle")}</p>'
                }
            },
            "events": timeline_items
        }
        
        # 更新时间线CSS样式
        st.markdown("""
            <style>
                /* 调整时间线标记的样式 */
                .tl-timemarker {
                    min-width: 120px !important;
                    max-width: 160px !important;
                }
                
                .tl-timemarker-content-container {
                    width: 120px !important;
                    min-width: 120px !important;
                }
                
                /* 调整文本大小和换行 */
                .tl-headline {
                    font-size: 11px !important;
                    line-height: 1.2 !important;
                    padding: 2px 4px !important;
                }
                
                /* 调整时间线导航栏高度 */
                .tl-timenav {
                    height: 180px !important;  /* Increased height */
                }
                
                /* 调整时间标记的高度和间距 */
                .tl-timemarker {
                    height: auto !important;
                    min-height: 85px !important;  /* Increased from 65px */
                    margin-bottom: 10px !important;  /* Added margin between markers */
                }
                
                .tl-timemarker-content-container {
                    height: auto !important;
                    min-height: 85px !important;  /* Increased from 65px */
                    padding: 4px !important;      /* Added padding */
                }
                
                /* 调整标题区域的样式 */
                .tl-headline {
                    padding: 4px 6px !important;  /* Increased padding */
                    line-height: 1.4 !important;  /* Increased line height */
                    margin-bottom: 4px !important;  /* Added margin */
                }
                
                /* 优化时间轴上的日期显示 */
                .tl-timeaxis-tick {
                    font-size: 10px !important;
                    color: #666 !important;
                }
                
                /* 确保标记之间有足够间距 */
                .tl-timemarker {
                    margin: 0 2px !important;
                }
                
                /* 优化时间线容器样式 */
                .tl-timeline {
                    font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei' !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Now use the timeline_config
        timeline(timeline_config, height=550)
        
    except Exception as e:
        logger.error(f"Error displaying timeline: {e}", exc_info=True)
        st.error(t('error.timeline_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_mood_distribution(start_date, end_date):
    """显示心情分布统计"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT mood, COUNT(*) as count
            FROM entries
            WHERE date BETWEEN ? AND ?
                AND mood IS NOT NULL
            GROUP BY mood
            ORDER BY count DESC
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_mood_data'))
            return
            
        from pyecharts import options as opts
        from pyecharts.charts import Pie
        from streamlit_echarts import st_pyecharts
        
        # 准备数据
        moods, counts = zip(*data)
        
        # 创建饼图
        c = (
            Pie()
            .add(
                "",
                [list(z) for z in zip(moods, counts)],
                radius=["40%", "75%"],
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="心情分布",
                    subtitle=f"从 {start_date} 到 {end_date}",
                    title_textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
                ),
                legend_opts=opts.LegendOpts(
                    orient="vertical",
                    pos_top="15%",
                    pos_left="2%",
                    textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
                ),
            )
            .set_series_opts(
                label_opts=opts.LabelOpts(
                    formatter="{b}: {c} ({d}%)",
                    font_family="Microsoft YaHei",
                )
            )
        )
        
        # 显示图表
        st_pyecharts(c)
        
    except Exception as e:
        logger.error(f"Error showing mood distribution: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_topic_wordcloud(start_date, end_date):
    """显示主题词云"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        # 查询主题数据
        query = """
            SELECT keywords, content
            FROM topics t
            JOIN entries e ON t.entry_id = e.id
            WHERE e.date BETWEEN ? AND ?
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_topics'))
            return
            
        # 使用jieba分词和pyecharts成词云
        import jieba
        from pyecharts import options as opts
        from pyecharts.charts import WordCloud as PyeWordCloud
        from streamlit_echarts import st_pyecharts
        
        # 处理关键词和内容
        text = ''
        for keywords, content in data:
            if keywords:
                text += ' ' + ' '.join(json.loads(keywords))
            if content:
                text += ' ' + content
                
        # 使用jieba分词
        words = jieba.cut(text)
        word_freq = {}
        for word in words:
            if len(word.strip()) > 1:  # 只统计长度大于1的词
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # 转换为pyecharts需要的格式
        words_data = [(word, freq) for word, freq in word_freq.items()]
        words_data.sort(key=lambda x: x[1], reverse=True)
        words_data = words_data[:100]  # 取前100个词
        
        # 创建词云图
        c = (
            PyeWordCloud()
            .add(
                "",
                words_data,
                word_size_range=[15, 80],
                textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="主题词云",
                    subtitle="基于日记内容分析",
                    title_textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
                ),
            )
        )
        
        # 显示词云
        st_pyecharts(c)
        
    except Exception as e:
        logger.error(f"Error showing topic wordcloud: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_word_count_stats(start_date, end_date):
    """显示字数统计"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT date, LENGTH(content) - LENGTH(REPLACE(content, ' ', '')) + 1 as word_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_entries'))
            return
            
        # 使用 plotly 绘制字数统计图
        import plotly.graph_objects as go
        
        dates, word_counts = zip(*data)
        fig = go.Figure(data=[go.Bar(
            x=dates,
            y=word_counts,
            name=t('insights.word_count')
        )])
        
        fig.update_layout(
            title=t('insights.word_count_stats'),
            xaxis_title=t('insights.date'),
            yaxis_title=t('insights.word_count'),
            height=400
        )
        
        st.plotly_chart(fig)
        
    except Exception as e:
        logger.error(f"Error showing word count stats: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_writing_time_distribution(start_date, end_date):
    """显示写作时间分布"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT strftime('%H', created_at) as hour,
                   COUNT(*) as entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY hour
            ORDER BY hour
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_entries'))
            return
            
        # 使用 plotly 绘制时间分布图
        import plotly.graph_objects as go
        
        hours, counts = zip(*data)
        fig = go.Figure(data=[go.Bar(
            x=hours,
            y=counts,
            name=t('insights.writing_time')
        )])
        
        fig.update_layout(
            title=t('insights.writing_time_distribution'),
            xaxis_title=t('insights.hour'),
            yaxis_title=t('insights.entry_count'),
            height=400
        )
        
        st.plotly_chart(fig)
        
    except Exception as e:
        logger.error(f"Error showing writing time distribution: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def get_all_tags():
    """获取所有标签"""
    try:
        db = init_db()
        if not db:
            return []
            
        cursor = db.execute('SELECT name FROM tags ORDER BY name')
        return [row[0] for row in cursor.fetchall()]
        
    except sqlite3.Error as e:
        logger.error(f"Error fetching tags: {e}")
        return []
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_topic_trends(start_date, end_date):
    """显示主题变化趋势"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT e.date, t.topic, COUNT(*) as count
            FROM topics t
            JOIN entries e ON t.entry_id = e.id
            WHERE e.date BETWEEN ? AND ?
            GROUP BY e.date, t.topic
            ORDER BY e.date, count DESC
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_topics'))
            return
            
        from pyecharts import options as opts
        from pyecharts.charts import ThemeRiver
        from streamlit_echarts import st_pyecharts
        
        # 转换数据格式为主题河流图所需的格式
        theme_data = []
        for date, topic, count in data:
            theme_data.append([date, count, topic])
        
        c = (
            ThemeRiver()
            .add(
                series_name=[],
                data=theme_data,
                singleaxis_opts=opts.SingleAxisOpts(
                    pos_top="50",
                    pos_bottom="50",
                    type_="time",
                ),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="主题变化趋势",
                    subtitle=f"从 {start_date} 到 {end_date}",
                ),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="line"
                ),
                legend_opts=opts.LegendOpts(
                    pos_top="15%",
                    orient="horizontal",
                    textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
                ),
            )
        )
        
        st_pyecharts(c)
        
    except Exception as e:
        logger.error(f"Error showing topic trends: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_key_events_timeline(start_date, end_date):
    """显示重要事件时间线"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        query = """
            SELECT e.date, e.title, e.content, t.sentiment
            FROM entries e
            LEFT JOIN topics t ON e.id = t.entry_id
            WHERE e.date BETWEEN ? AND ?
                AND t.sentiment IS NOT NULL
            ORDER BY t.sentiment DESC
            LIMIT 10
        """
        cursor = db.execute(query, (start_date, end_date))
        events = cursor.fetchall()
        
        if not events:
            st.info(t('insights.no_key_events'))
            return
            
        st.markdown(f"### {t('insights.key_events')}")
        for date, title, content, sentiment in events:
            with st.expander(f"{date}: {title}"):
                st.write(content[:200] + "..." if len(content) > 200 else content)
                st.caption(f"{t('insights.sentiment')}: {sentiment:.2f}")
                
    except Exception as e:
        logger.error(f"Error showing key events: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

def show_growth_indicators(start_date, end_date):
    """显示个人成长指标"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        # 获取写作量数据
        writing_query = """
            SELECT date, LENGTH(content) as length,
                   COUNT(*) as entry_count
            FROM entries
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        """
        cursor = db.execute(writing_query, (start_date, end_date))
        writing_data = cursor.fetchall()
        
        if writing_data:
            from pyecharts import options as opts
            from pyecharts.charts import Line, Grid
            from streamlit_echarts import st_pyecharts
            
            dates = [row[0] for row in writing_data]
            lengths = [row[1] for row in writing_data]
            counts = [row[2] for row in writing_data]
            
            # 创建写作量趋势图
            line = (
                Line()
                .add_xaxis(dates)
                .add_yaxis(
                    "字数",
                    lengths,
                    symbol_size=8,
                    color="#1976D2",
                    is_smooth=True,
                )
                .add_yaxis(
                    "日记数",
                    counts,
                    symbol_size=8,
                    color="#4CAF50",
                    is_smooth=True,
                )
                .set_global_opts(
                    title_opts=opts.TitleOpts(
                        title="写作成长趋势",
                        subtitle=f"从 {start_date} 到 {end_date}",
                        title_textstyle_opts=opts.TextStyleOpts(font_family="Microsoft YaHei"),
                    ),
                    xaxis_opts=opts.AxisOpts(
                        type_="category",
                        name="日期",
                        name_location="end",
                        axislabel_opts=opts.LabelOpts(rotate=45),
                    ),
                    yaxis_opts=opts.AxisOpts(
                        type_="value",
                        name="数量",
                        name_location="end",
                        splitline_opts=opts.SplitLineOpts(is_show=True),
                    ),
                    legend_opts=opts.LegendOpts(
                        pos_top="5%",
                        pos_left="center",
                        orient="horizontal",
                    ),
                    tooltip_opts=opts.TooltipOpts(trigger="axis"),
                )
            )
            
            st_pyecharts(line)
            
            # 显示统计指标
            col1, col2 = st.columns(2)
            with col1:
                avg_length = sum(lengths) / len(lengths)
                st.metric(
                    "平均字数",
                    f"{int(avg_length)}",
                    delta=f"{int(lengths[-1] - avg_length)}"
                )
            with col2:
                avg_count = sum(counts) / len(counts)
                st.metric(
                    "平均日记数",
                    f"{avg_count:.1f}",
                    delta=f"{counts[-1] - avg_count:.1f}"
                )
        
    except Exception as e:
        logger.error(f"Error showing growth indicators: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

if __name__ == "__main__":
    main() 
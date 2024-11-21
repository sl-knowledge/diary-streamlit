import streamlit as st
import sqlite3
from datetime import datetime
import json
from pathlib import Path
import uuid
import shutil
import logging
import os
from src.config import Config
from src.i18n.manager import t, I18nManager

# 使用 Config 类的属性
config = Config()
ALLOWED_EXTENSIONS = config.APP_CONFIG['allowed_extensions']

logging.basicConfig(level=logging.DEBUG if Config.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

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

def save_entry(title, content, uploaded_files):
    """Save entry with attachments"""
    db = init_db()
    entry_id = str(uuid.uuid4())
    
    # Save uploaded files
    attachment_paths = []
    if uploaded_files:
        for file in uploaded_files:
            path = save_uploaded_file(file)
            if path:
                attachment_paths.append(path)
    
    # Save entry to database with correct fields
    db.execute('''
        INSERT INTO entries (id, date, title, content, attachments)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        entry_id,
        datetime.now().strftime('%Y-%m-%d'),
        title,
        content,
        json.dumps(attachment_paths)
    ))
    db.commit()
    db.close()

def init_app():
    """Initialize application directories and database"""
    try:
        # 使用 Config 实例的属性
        config.DATA_DIR.mkdir(exist_ok=True)
        config.UPLOAD_DIR.mkdir(exist_ok=True)
        
        # 验证权限
        if not os.access(config.DATA_DIR, os.W_OK):
            logger.error(f"No write access to {config.DATA_DIR}")
            raise PermissionError(f"No write access to {config.DATA_DIR}")
            
        return True
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        return False

def main():
    st.set_page_config(page_title=t('app.title'), layout="wide")
    
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
            start_date = st.date_input(t('timeline.start_date'))
            end_date = st.date_input(t('timeline.end_date'))
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
    
    # 时间范围选择 - 添加唯一的 key
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            t('insights.period_start'),
            key='insights_start_date'  # 添加唯一key
        )
    with col2:
        end_date = st.date_input(
            t('insights.period_end'),
            key='insights_end_date'  # 添加唯一key
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
            
        # 查询情绪数据
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
            
        # 使用 plotly 绘制情绪趋势图
        import plotly.graph_objects as go
        
        # 处理数据...
        st.plotly_chart(fig)
        
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
            
        # 查询写作频率
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
            
        # 使用 plotly 绘制频率图表
        import plotly.graph_objects as go
        
        # 处理数据...
        st.plotly_chart(fig)
        
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
        save_entry(title, content, uploaded_files)
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
        
        # 添加数据库连接验证
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

def show_filtered_entries(filter_type, filter_params):
    """Display filtered entries based on selected filter type"""
    try:
        logger.debug(f"Fetching entries with filter_type: {filter_type}")
        db = init_db()
        if not db:
            logger.error("Database connection failed")
            st.error(t('error.db_connect'))
            return

        # 基础查询
        query = """
            SELECT e.id, e.date, e.title, e.content, e.mood, e.weather, 
                   e.location, e.attachments, e.created_at
            FROM entries e
        """
        params = []
        where_clauses = []

        # 根据过滤类型构建查询
        if filter_type == t('timeline.date_range'):
            start_date = filter_params.get('start_date')
            end_date = filter_params.get('end_date')
            if start_date and end_date:
                where_clauses.append("date BETWEEN ? AND ?")
                params.extend([start_date.strftime('%Y-%m-%d'), 
                             end_date.strftime('%Y-%m-%d')])
                logger.debug(f"Date range filter: {start_date} to {end_date}")

        elif filter_type == t('timeline.tags'):
            selected_tags = filter_params.get('selected_tags', [])
            if selected_tags:
                placeholders = ','.join(['?' for _ in selected_tags])
                query += """
                    JOIN entry_tags et ON e.id = et.entry_id
                    JOIN tags t ON et.tag_id = t.id
                """
                where_clauses.append(f"t.name IN ({placeholders})")
                params.extend(selected_tags)
                logger.debug(f"Selected tags: {selected_tags}")

        elif filter_type == t('timeline.search'):
            search_query = filter_params.get('search_query', '')
            if search_query:
                query += " JOIN entries_fts ON e.id = entries_fts.rowid"
                where_clauses.append("entries_fts MATCH ?")
                params.append(search_query)
                logger.debug(f"Search query: {search_query}")

        # 添加 WHERE 子句
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # 添加排序
        query += " ORDER BY date DESC, created_at DESC"

        logger.debug(f"Executing query: {query}")
        logger.debug(f"Query parameters: {params}")

        # 执行查询
        cursor = db.execute(query, params)
        entries = cursor.fetchall()
        logger.debug(f"Found {len(entries)} entries")

        if not entries:
            st.info(t('common.no_data'))
            return

        # 显示条目
        for entry in entries:
            with st.expander(f"{entry[1]} - {entry[2]}", expanded=False):
                # 显示内容
                st.write(entry[3])
                
                # 显示元数据
                cols = st.columns(3)
                with cols[0]:
                    if entry[4]:  # mood
                        st.caption(f"{t('editor.mood')}: {entry[4]}")
                with cols[1]:
                    if entry[5]:  # weather
                        st.caption(f"{t('editor.weather')}: {entry[5]}")
                with cols[2]:
                    if entry[6]:  # location
                        st.caption(f"{t('editor.location')}: {entry[6]}")
                
                # 显示附件
                if entry[7]:  # attachments
                    try:
                        attachments = json.loads(entry[7])
                        if attachments:
                            st.write(t('editor.attachments'))
                            image_cols = st.columns(4)
                            for idx, attachment in enumerate(attachments):
                                with image_cols[idx % 4]:
                                    if Path(attachment).suffix.lower() in ALLOWED_EXTENSIONS:
                                        st.image(f"data/{attachment}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse attachments JSON: {e}")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}", exc_info=True)
        st.error(t('error.db_query'))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        st.error(t('error.unexpected'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()
            logger.debug("Database connection closed")

def show_mood_distribution(start_date, end_date):
    """显示心情分布统计"""
    try:
        db = init_db()
        if not db:
            st.error(t('error.db_connect'))
            return
            
        # 查询心情数据
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
            
        # 使用 plotly 绘制饼图
        import plotly.graph_objects as go
        
        moods, counts = zip(*data)
        fig = go.Figure(data=[go.Pie(
            labels=moods,
            values=counts,
            hole=.3,
            title=t('insights.mood_distribution')
        )])
        
        fig.update_layout(
            showlegend=True,
            height=400,
            margin=dict(t=0, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig)
        
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
            SELECT keywords
            FROM topics t
            JOIN entries e ON t.entry_id = e.id
            WHERE e.date BETWEEN ? AND ?
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_topics'))
            return
            
        # 处理关键词数据
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        
        # 合并所有关键词
        all_keywords = ' '.join([kw for row in data for kw in json.loads(row[0])])
        
        # 生成词云
        wordcloud = WordCloud(
            width=800, 
            height=400,
            background_color='white',
            max_words=100
        ).generate(all_keywords)
        
        # 显示词云
        fig, ax = plt.subplots()
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
        
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
            SELECT t.topic, e.date, COUNT(*) as count
            FROM topics t
            JOIN entries e ON t.entry_id = e.id
            WHERE e.date BETWEEN ? AND ?
            GROUP BY t.topic, e.date
            ORDER BY e.date, count DESC
        """
        cursor = db.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        if not data:
            st.info(t('insights.no_topics'))
            return
            
        # 使用 plotly 绘制趋势图
        import plotly.graph_objects as go
        
        # 处理数据为时间序列格式
        topics_data = {}
        for topic, date, count in data:
            if topic not in topics_data:
                topics_data[topic] = {'dates': [], 'counts': []}
            topics_data[topic]['dates'].append(date)
            topics_data[topic]['counts'].append(count)
        
        fig = go.Figure()
        for topic, values in topics_data.items():
            fig.add_trace(go.Scatter(
                x=values['dates'],
                y=values['counts'],
                name=topic,
                mode='lines+markers'
            ))
        
        fig.update_layout(
            title=t('insights.topic_trends'),
            xaxis_title=t('insights.date'),
            yaxis_title=t('insights.count'),
            height=500
        )
        
        st.plotly_chart(fig)
        
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
            
        # 获取写作量增长
        writing_query = """
            SELECT date, LENGTH(content) as length
            FROM entries
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """
        cursor = db.execute(writing_query, (start_date, end_date))
        writing_data = cursor.fetchall()
        
        if writing_data:
            st.subheader(t('insights.writing_growth'))
            # 计算写作量趋势
            lengths = [x[1] for x in writing_data]
            avg_length = sum(lengths) / len(lengths)
            st.metric(
                t('insights.avg_length'),
                f"{int(avg_length)} {t('insights.characters')}"
            )
            
        # 获取情感变化
        mood_query = """
            SELECT date, mood
            FROM entries
            WHERE date BETWEEN ? AND ?
                AND mood IS NOT NULL
            ORDER BY date
        """
        cursor = db.execute(mood_query, (start_date, end_date))
        mood_data = cursor.fetchall()
        
        if mood_data:
            st.subheader(t('insights.mood_growth'))
            # 展示情感变化图表
            
    except Exception as e:
        logger.error(f"Error showing growth indicators: {e}")
        st.error(t('error.analysis_failed'))
    finally:
        if 'db' in locals() and db is not None:
            db.close()

if __name__ == "__main__":
    main() 
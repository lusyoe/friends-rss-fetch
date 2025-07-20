import logging
import os
from dotenv import load_dotenv
from pyxxl import ExecutorConfig, PyxxlRunner
from pyxxl.ctx import g
import pymysql
import feedparser
from datetime import datetime

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置pyxxl框架的日志
pyxxl_logger = logging.getLogger('pyxxl')
pyxxl_logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# 添加处理器到pyxxl logger
pyxxl_logger.addHandler(console_handler)

# 如果xxl-admin可以直连executor的ip，可以不填写executor_listen_host
config = ExecutorConfig(
    xxl_admin_baseurl=os.getenv("XXL_ADMIN_BASEURL", "http://xxljob.luhome.com/xxl-job-admin/api/"),
    executor_app_name=os.getenv("EXECUTOR_APP_NAME", "python-rss-fetch-executor"),
    executor_url=os.getenv("EXECUTOR_URL", "http://192.168.10.1:9999"),
    executor_listen_host=os.getenv("EXECUTOR_LISTEN_HOST", "0.0.0.0"),
    executor_listen_port=int(os.getenv("EXECUTOR_LISTEN_PORT", "9999")),
    access_token=os.getenv("ACCESS_TOKEN", "default_token"),
)

# 数据库连接配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_DATABASE", "blog"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4")
}

app = PyxxlRunner(config)

def get_friend_links(conn):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT id, rss_url 
            FROM friend_links 
            WHERE rss_url IS NOT NULL 
            AND rss_url != '' 
            AND is_active = 1
        """)
        return cursor.fetchall()

def fetch_rss_articles(rss_url):
    feed = feedparser.parse(rss_url)
    articles = []
    
    # 检查feed类型并记录
    feed_type = "未知"
    if hasattr(feed, 'version'):
        if 'rss' in feed.version.lower():
            feed_type = "RSS"
        elif 'atom' in feed.version.lower():
            feed_type = "Atom"
    
    g.logger.info(f"    检测到Feed类型: {feed_type}")
    
    for entry in feed.entries:
        title = entry.get('title', '')
        link = entry.get('link', '')
        
        # 发布时间兼容RSS和Atom格式
        published_time = None
        
        # 根据feed类型选择合适的时间字段
        if feed_type == "RSS":
            # RSS格式优先使用pubDate和published字段
            time_fields = [
                ('pubDate_parsed', 'pubDate'),
                ('published_parsed', 'published')
            ]
        elif feed_type == "Atom":
            # Atom格式优先使用updated和published字段
            time_fields = [
                ('updated_parsed', 'updated'),
                ('published_parsed', 'published'),
                ('created_parsed', 'created'),
                ('modified_parsed', 'modified')
            ]
        else:
            # 未知格式，尝试所有字段
            time_fields = [
                ('published_parsed', 'published'),
                ('updated_parsed', 'updated'),
                ('pubDate_parsed', 'pubDate'),
                ('created_parsed', 'created'),
                ('modified_parsed', 'modified')
            ]
        
        for parsed_field, raw_field in time_fields:
            if hasattr(entry, parsed_field) and getattr(entry, parsed_field):
                try:
                    parsed_time = getattr(entry, parsed_field)
                    published_time = datetime(*parsed_time[:6])
                    break
                except Exception:
                    continue
        
        # 如果没有解析的时间，尝试解析原始时间字符串
        if published_time is None:
            if feed_type == "RSS":
                raw_time_fields = ['pubDate', 'published']
            elif feed_type == "Atom":
                raw_time_fields = ['updated', 'published', 'created', 'modified']
            else:
                raw_time_fields = ['published', 'updated', 'pubDate', 'created', 'modified']
            
            for field in raw_time_fields:
                raw_time = entry.get(field, '')
                if raw_time:
                    try:
                        # feedparser会自动尝试解析时间
                        if hasattr(entry, f'{field}_parsed') and getattr(entry, f'{field}_parsed'):
                            parsed_time = getattr(entry, f'{field}_parsed')
                            published_time = datetime(*parsed_time[:6])
                            break
                    except Exception:
                        continue
        
        articles.append({
            "title": title,
            "link": link,
            "created_at": published_time
        })
    
    return articles

def article_exists(conn, friend_id, link):
    with conn.cursor() as cursor:
        sql = "SELECT 1 FROM friend_rss_articles WHERE friend_id=%s AND link=%s LIMIT 1"
        cursor.execute(sql, (friend_id, link))
        return cursor.fetchone() is not None

def save_articles(conn, friend_id, articles):
    to_insert = []
    for article in articles:
        if not article['title'] or not article['link']:
            continue
        if article_exists(conn, friend_id, article['link']):
            continue
        to_insert.append((
            friend_id,
            article['title'],
            article['link'],
            article['created_at'] if article['created_at'] else None
        ))
        if len(to_insert) == 100:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO friend_rss_articles (friend_id, title, link, created_at)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.executemany(sql, to_insert)
            conn.commit()
            to_insert = []
    # 插入剩余不足100条的部分
    if to_insert:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO friend_rss_articles (friend_id, title, link, created_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.executemany(sql, to_insert)
        conn.commit()

def update_fetch_failed_count(conn, friend_id, failed_count):
    """更新fetch_failed_count字段，当达到3次时停用友链"""
    with conn.cursor() as cursor:
        if failed_count >= 3:
            # 当失败次数达到3次时，停用友链
            sql = "UPDATE friend_links SET fetch_failed_count = %s, is_active = 0 WHERE id = %s"
            cursor.execute(sql, (failed_count, friend_id))
            g.logger.info(f"  🚫 friend_id={friend_id} 失败次数达到3次，已停用")
        else:
            # 正常更新失败计数
            sql = "UPDATE friend_links SET fetch_failed_count = %s WHERE id = %s"
            cursor.execute(sql, (failed_count, friend_id))
    conn.commit()

def reset_fetch_failed_count(conn, friend_id):
    """抓取成功后重置失败计数"""
    with conn.cursor() as cursor:
        sql = "UPDATE friend_links SET fetch_failed_count = 0 WHERE id = %s"
        cursor.execute(sql, (friend_id,))
    conn.commit()

def insert_fetch_log(conn, friend_id, rss_url, status, http_status=None, message=None):
    """写入抓取日志到friend_rss_fetch_logs表"""
    with conn.cursor() as cursor:
        sql = """
            INSERT INTO friend_rss_fetch_logs (friend_id, rss_url, status, http_status, message, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            friend_id,
            rss_url,
            status,
            http_status,
            message,
            datetime.now()
        ))
    conn.commit()

def insert_fetch_logs_batch(conn, logs):
    """批量写入抓取日志到friend_rss_fetch_logs表"""
    if not logs:
        return
    with conn.cursor() as cursor:
        sql = """
            INSERT INTO friend_rss_fetch_logs (friend_id, rss_url, status, http_status, message, fetched_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        data = [
            (
                log['friend_id'],
                log['rss_url'],
                log['status'],
                log.get('http_status'),
                log.get('message'),
                log['fetched_at']
            ) for log in logs
        ]
        cursor.executemany(sql, data)
    conn.commit()


@app.register(name="rss_fetch")
async def rss_fetch():
    """
    定时获取rss订阅信息
    """
    conn = pymysql.connect(**DB_CONFIG)
    try:
        links = get_friend_links(conn)
        g.logger.info(f"共找到 {len(links)} 个激活的友链有 RSS")
        
        # 记录统计信息
        success_count = 0
        failed_count = 0
        zero_articles_count = 0
        zero_articles_links = []
        failed_links = []
        deactivated_links = []
        fetch_logs = []  # 新增日志收集列表
        
        for friend_id, rss_url in links:
            g.logger.info(f"\n抓取 friend_id={friend_id} 的 RSS: {rss_url}")
            try:
                articles = fetch_rss_articles(rss_url)
                g.logger.info(f"  发现 {len(articles)} 篇文章")
                
                if len(articles) == 0:
                    # 记录发现0篇文章的链接
                    zero_articles_count += 1
                    zero_articles_links.append({
                        'friend_id': friend_id,
                        'rss_url': rss_url
                    })
                    g.logger.info("  ⚠️  发现0篇文章")
                    # 增加失败计数
                    failed_links.append(friend_id)
                    # 收集日志
                    fetch_logs.append({
                        'friend_id': friend_id,
                        'rss_url': rss_url,
                        'status': 'zero_articles',
                        'http_status': None,
                        'message': '发现0篇文章',
                        'fetched_at': datetime.now()
                    })
                else:
                    g.logger.info("  正在入库...")
                    save_articles(conn, friend_id, articles)
                    g.logger.info("  入库完成")
                    reset_fetch_failed_count(conn, friend_id)  # 抓取成功后清空失败次数
                    success_count += 1
                    # 收集日志
                    fetch_logs.append({
                        'friend_id': friend_id,
                        'rss_url': rss_url,
                        'status': 'success',
                        'http_status': None,
                        'message': f'成功抓取{len(articles)}篇文章',
                        'fetched_at': datetime.now()
                    })
                    
            except Exception as e:
                error_msg = str(e)
                g.logger.error(f"  ❌ 抓取或入库失败: {error_msg}")
                failed_count += 1
                # 增加失败计数
                failed_links.append(friend_id)
                # 收集日志
                fetch_logs.append({
                    'friend_id': friend_id,
                    'rss_url': rss_url,
                    'status': 'fail',
                    'http_status': None,
                    'message': error_msg,
                    'fetched_at': datetime.now()
                })
        
        # 更新数据库中的fetch_failed_count字段
        g.logger.info(f"\n正在更新数据库中的fetch_failed_count字段...")
        for friend_id in failed_links:
            # 获取当前失败计数并加1
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(fetch_failed_count, 0) FROM friend_links WHERE id = %s", (friend_id,))
                current_count = cursor.fetchone()[0]
                new_count = current_count + 1
                update_fetch_failed_count(conn, friend_id, new_count)
                
                if new_count >= 3:
                    deactivated_links.append(friend_id)
                else:
                    g.logger.info(f"  更新 friend_id={friend_id}: fetch_failed_count = {new_count}")
        
        # 循环结束后统一批量插入日志
        insert_fetch_logs_batch(conn, fetch_logs)

        # 输出统计信息
        g.logger.info(f"\n{'='*50}")
        g.logger.info("抓取完成统计:")
        g.logger.info(f"激活的友链数: {len(links)}")
        g.logger.info(f"成功抓取: {success_count}")
        g.logger.info(f"抓取失败: {failed_count}")
        g.logger.info(f"发现0篇文章: {zero_articles_count}")
        g.logger.info(f"需要更新fetch_failed_count的链接数: {len(failed_links)}")
        g.logger.info(f"因失败次数过多而停用的链接数: {len(deactivated_links)}")
        
        if zero_articles_links:
            g.logger.info(f"\n发现0篇文章的链接:")
            for link in zero_articles_links:
                g.logger.info(f"  - friend_id={link['friend_id']}: {link['rss_url']}")
            g.logger.info(f"发现0篇文章的链接数: {len(zero_articles_links)}")
        if deactivated_links:
            g.logger.info(f"\n因失败次数过多而停用的链接:")
            for friend_id in deactivated_links:
                g.logger.info(f"  - friend_id={friend_id}")
        
        g.logger.info(f"{'='*50}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    app.run_executor()

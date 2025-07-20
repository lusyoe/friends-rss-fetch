# RSS Fetch Schedule

一个基于 XXL-JOB 的 RSS 订阅内容定时抓取服务，用于自动获取友链博客的最新文章并存储到数据库中。

# 相关项目
- [Friends 前端展示](https://github.com/lusyoe/friends-frontend)
- [Friends 后端接口](https://github.com/lusyoe/friends-api)

[博客地址-青萍叙事](https://blog.lusyoe.com)

## 项目简介

本项目是一个 Python 编写的 RSS 内容抓取服务，主要功能是：
- 定时抓取友链博客的 RSS 订阅内容
- 自动解析 RSS/Atom 格式的订阅源
- 将抓取到的文章信息存储到 MySQL 数据库
- 支持失败重试机制和自动停用异常友链
- 提供详细的抓取日志和统计信息

## 功能特性

### 🔄 自动抓取
- 支持 RSS 和 Atom 格式的订阅源
- 自动解析文章标题、链接和发布时间
- 批量处理，提高抓取效率

### 🛡️ 容错机制
- 失败重试计数，连续失败3次自动停用友链
- 抓取成功后自动重置失败计数
- 详细的错误日志记录

### 📊 监控统计
- 实时显示抓取进度和结果
- 统计成功/失败数量和原因
- 记录抓取日志到数据库

### 🐳 容器化部署
- 提供 Dockerfile 支持容器化部署
- 使用 Python 3.11 基础镜像
- 支持国内镜像源加速

## 技术栈

- **Python 3.13+**: 主要开发语言
- **UV**: 现代化的 Python 包管理器和项目工具
- **PyXXL**: XXL-JOB Python 执行器框架
- **feedparser**: RSS/Atom 解析库
- **PyMySQL**: MySQL 数据库连接
- **Docker**: 容器化部署

## 项目结构

```
rss-fetch-schedule/
├── main.py              # 主程序文件
├── pyproject.toml       # 项目依赖配置
├── uv.lock              # UV 锁定文件
├── Dockerfile           # Docker 构建文件
├── README.md            # 项目说明文档
├── .python-version      # Python 版本文件
├── .gitignore           # Git 忽略文件
└── .venv/               # 虚拟环境目录
```

## 安装部署

### 环境要求

- Python 3.13+
- UV 包管理器
- MySQL 数据库
- XXL-JOB 调度中心

### 本地开发环境

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd rss-fetch-schedule
   ```

2. **安装 UV 包管理器**
   ```bash
   # 使用官方安装脚本
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # 或使用 pip 安装
   pip install uv
   ```

3. **创建虚拟环境并安装依赖**
   ```bash
   # UV 会自动创建虚拟环境并安装依赖
   uv sync
   ```

4. **激活虚拟环境**
   ```bash
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   ```

5. **配置环境变量**
   复制环境变量配置文件：
   ```bash
   cp env.example .env
   ```

6. **运行服务**
   ```bash
   python main.py
   ```

### Docker 部署

1. **构建镜像**
   ```bash
   docker build -t rss-fetch-schedule .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name rss-fetch-schedule \
     -p 9999:9999 \
     -e DB_HOST=your-database-host \
     -e DB_USER=your-username \
     -e DB_PASSWORD=your-password \
     -e DB_NAME=your-database-name \
     -e XXL_ADMIN_BASEURL=http://your-xxl-job-admin/api/ \
     -e XXL_EXECUTOR_APP_NAME=python-rss-fetch-executor \
     -e XXL_EXECUTOR_URL=http://your-executor-ip:9999 \
     -e XXL_EXECUTOR_LISTEN_HOST=0.0.0.0 \
     -e XXL_EXECUTOR_LISTEN_PORT=9999 \
     -e XXL_ACCESS_TOKEN=your-access-token \
     rss-fetch-schedule
   ```

## 配置说明

#### 数据库配置环境变量
- `DB_HOST`: 数据库主机地址
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码
- `DB_NAME`: 数据库名称
- `DB_CHARSET`: 字符集编码，默认为 `utf8mb4`

#### XXL-JOB 配置环境变量
- `XXL_ADMIN_BASEURL`: XXL-JOB 管理后台地址
- `XXL_EXECUTOR_APP_NAME`: 执行器应用名称
- `XXL_EXECUTOR_URL`: 执行器访问地址
- `XXL_EXECUTOR_LISTEN_HOST`: 执行器监听主机，默认为 `0.0.0.0`
- `XXL_EXECUTOR_LISTEN_PORT`: 执行器监听端口，默认为 `9999`
- `XXL_ACCESS_TOKEN`: 访问令牌

## 使用说明

### 任务注册

服务启动后会自动注册名为 `rss_fetch` 的任务到 XXL-JOB 调度中心。

### 任务执行

在 XXL-JOB 管理后台创建定时任务：
- **任务名称**: rss_fetch
- **执行器**: python-rss-fetch-executor
- **Cron 表达式**: 根据需要设置，如 `0 00 02 * * ? *` (每天凌晨2点执行一次)

### 监控日志

任务执行时会输出详细的日志信息，包括：
- 抓取的友链数量
- 每篇文章的抓取状态
- 成功/失败统计
- 异常友链的处理情况

## 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查数据库配置是否正确
   - 确认数据库服务是否正常运行
   - 验证网络连接是否通畅

2. **RSS 抓取失败**
   - 检查 RSS 地址是否有效
   - 确认网络连接是否正常
   - 查看详细错误日志

3. **XXL-JOB 连接失败**
   - 检查 XXL-JOB 管理后台地址
   - 确认执行器配置是否正确
   - 验证访问令牌是否有效

### 日志查看

```bash
# 查看容器日志
docker logs rss-fetch-schedule

# 查看实时日志
docker logs -f rss-fetch-schedule
```

## 开发说明

### 代码结构

- `main.py`: 主程序文件，包含所有业务逻辑
- `rss_fetch()`: 主要的抓取任务函数
- `fetch_rss_articles()`: RSS 内容解析函数
- `save_articles()`: 文章数据保存函数
- `update_fetch_failed_count()`: 失败计数更新函数

### 依赖管理

本项目使用 UV 包管理器进行依赖管理：

```bash
# 添加新依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 更新依赖
uv sync

# 运行脚本
uv run python main.py
```

### 扩展开发

如需添加新功能，可以：
1. 在 `main.py` 中添加新的任务函数
2. 使用 `@app.register(name="task_name")` 装饰器注册任务
3. 在 XXL-JOB 管理后台创建对应的定时任务

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 发送邮件至项目维护者

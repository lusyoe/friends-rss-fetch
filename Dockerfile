FROM python:3.11-slim

WORKDIR /app

ENV INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ENV TZ=Asia/Shanghai

# 复制依赖文件
COPY pyproject.toml .

# 安装 UV
RUN pip install --no-cache-dir uv -i $INDEX_URL

# 安装依赖
RUN uv pip install --system -r pyproject.toml --index $INDEX_URL

RUN sed -i 's|http://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources

# 复制后端代码
COPY . /app

EXPOSE 9999

CMD ["python", "main.py"]
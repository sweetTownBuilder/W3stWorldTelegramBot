# 使用官方 Python 运行时作为父镜像
FROM python:3.10.11

# 设置工作目录为 /app
WORKDIR /app

# 将当前目录内容复制到容器的 /app 中
COPY . /app

# 安装所需包
RUN pip install --no-cache-dir -r requirements.txt

# 容器启动时运行的命令
CMD ["python", "-m", "src.bot"]
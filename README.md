# Demo

一个最小 Python 后端 demo，提供 HTTP 接口和文件日志。

## 运行

```bash
cd /Users/cyl/projects/BoostVision-AI-Workshop/github-issue-fix-agent/demo
python3 run.py
```

默认监听：

```bash
http://127.0.0.1:8000
```

## 接口

```bash
GET /health
GET /api/echo?message=hello
POST /api/echo
```

POST 示例：

```bash
curl -X POST http://127.0.0.1:8000/api/echo \
  -H 'Content-Type: application/json' \
  -d '{"message":"hello"}'
```

## 日志

日志文件输出到：

```bash
/Users/cyl/projects/BoostVision-AI-Workshop/github-issue-fix-agent/demo/logs/app.log
```

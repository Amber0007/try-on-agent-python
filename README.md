# AI 虚拟试衣 Agent - Python 版

淘宝服装图片 → 数字人穿搭效果生成工具

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 3. 启动服务

```bash
python app.py
# 访问 http://localhost:5000
```

## 项目结构

```
try-on-agent-python/
├── app.py                 # 主程序（Flask 服务器）
├── services/              # 服务模块
│   ├── dashscope.py       # 阿里云 API 客户端
│   ├── outfit.py          # 服装处理
│   ├── avatar.py          # 数字人管理
│   └── knowledge.py       # 穿搭知识库
├── static/                # 静态文件
├── templates/             # HTML 模板
├── data/                  # 数据存储
│   ├── avatars/           # 数字人图片
│   ├── outfits/           # 服装图片
│   └── knowledge/         # 穿搭知识
├── requirements.txt
└── .env.example
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/try-on` | POST | 执行虚拟试衣 |
| `/api/avatars` | GET | 获取数字人列表 |
| `/api/outfits` | GET | 获取服装列表 |
| `/api/outfits/upload` | POST | 上传服装图片 |
| `/api/knowledge` | GET | 获取穿搭知识 |

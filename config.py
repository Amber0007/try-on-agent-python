"""
配置文件
"""
import os
from pathlib import Path

# 基础目录
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# API 配置
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY', '')

# DashScope API 配置
DASHSCOPE_BASE_URL = 'https://dashscope.aliyuncs.com/api/v1'
DASHSCOPE_VTON_MODEL = 'wanx-virtual-try-on-v1'
DASHSCOPE_VL_MODEL = 'qwen-vl-max'

# Remove.bg API 配置
REMOVE_BG_BASE_URL = 'https://api.remove.bg/v1.0'

# 数字人预设
AVATAR_CONFIG = {
    'body_types': ['slim', 'standard', 'curvy', 'plus'],
    'skin_tones': ['fair', 'light', 'medium', 'olive', 'dark'],
    'poses': ['standing_front', 'standing_side', 'sitting', 'walking']
}

# 穿搭知识库配置
KNOWLEDGE_CONFIG = {
    'styles': ['casual', 'formal', 'sporty', 'elegant', 'street', 'minimalist'],
    'seasons': ['spring', 'summer', 'autumn', 'winter'],
    'occasions': ['daily', 'work', 'party', 'date', 'travel']
}

# 数据目录配置
PATHS = {
    'avatars': DATA_DIR / 'avatars',
    'outfits': DATA_DIR / 'outfits',
    'knowledge': DATA_DIR / 'knowledge',
    'uploads': DATA_DIR / 'uploads',
    'outputs': DATA_DIR / 'outputs'
}

# 确保数据目录存在
def ensure_data_directories():
    """创建必要的目录"""
    for path in PATHS.values():
        path.mkdir(parents=True, exist_ok=True)

    # 创建子目录
    (PATHS['avatars'] / 'base').mkdir(exist_ok=True)
    (PATHS['avatars'] / 'generated').mkdir(exist_ok=True)
    (PATHS['outfits'] / 'original').mkdir(exist_ok=True)
    (PATHS['outfits'] / 'masked').mkdir(exist_ok=True)
    (PATHS['knowledge'] / 'images').mkdir(exist_ok=True)
    (PATHS['knowledge'] / 'rules').mkdir(exist_ok=True)

"""
穿搭知识库服务
管理穿搭图片、技巧、搭配规则
"""
import json
import uuid
import typing
import requests
from pathlib import Path
from datetime import datetime
from config import PATHS, DASHSCOPE_API_KEY, KNOWLEDGE_CONFIG
from services.dashscope import DashScopeService


class KnowledgeService:
    """穿搭知识库服务"""

    def __init__(self):
        self.storage_path = PATHS['knowledge']
        self.rules_path = self.storage_path / 'rules' / 'default-rules.json'
        self.outfits_path = self.storage_path / 'outfits.json'
        self.dashscope_service = DashScopeService(DASHSCOPE_API_KEY) if DASHSCOPE_API_KEY else None
        self._ensure_directories()
        self._init_knowledge()

    def _ensure_directories(self):
        """确保目录存在"""
        (self.storage_path / 'images').mkdir(parents=True, exist_ok=True)
        (self.storage_path / 'rules').mkdir(parents=True, exist_ok=True)

    def _init_knowledge(self):
        """初始化默认穿搭知识"""
        # 初始化穿搭规则
        if not self.rules_path.exists():
            default_rules = {
                'colorMatching': [
                    {'name': '同色系', 'description': '使用相同色系的不同深浅度，营造和谐统一的感觉', 'example': '深蓝上衣 + 浅蓝裤子'},
                    {'name': '互补色', 'description': '使用色轮上相对的颜色，创造鲜明对比', 'example': '蓝色 + 橙色，红色 + 绿色'},
                    {'name': '类似色', 'description': '使用色轮上相邻的颜色，柔和有层次', 'example': '蓝色 + 紫色，红色 + 橙色'},
                    {'name': '中性色百搭', 'description': '黑白灰棕等中性色几乎可以搭配任何颜色', 'example': '白色 T 恤 + 任何颜色外套'}
                ],
                'styleRules': [
                    {'style': 'casual', 'name': '休闲风', 'tips': ['舒适为主', '避免过于正式', '可搭配运动鞋/帆布鞋', '层次穿搭增加趣味']},
                    {'style': 'formal', 'name': '正式风', 'tips': ['剪裁合身', '颜色简洁', '注意细节', '配饰要精致']},
                    {'style': 'sporty', 'name': '运动风', 'tips': ['功能性面料', '宽松舒适', '运动鞋必备', '可加运动帽']},
                    {'style': 'elegant', 'name': '优雅风', 'tips': ['简约线条', '高质量面料', '避免过多装饰', '配饰点睛']},
                    {'style': 'street', 'name': '街头风', 'tips': ['oversize 元素', '印花/图案', '混搭色彩', '潮流单品']},
                    {'style': 'minimalist', 'name': '极简风', 'tips': ['纯色为主', '去除多余装饰', '注重质感', '少即是多']}
                ],
                'bodyTypeTips': [
                    {'bodyType': 'slim', 'name': '纤瘦型', 'tips': ['层叠穿搭增加体积感', '避免过于紧身', '横条纹视觉增宽', '选择有质感的面料']},
                    {'bodyType': 'standard', 'name': '标准型', 'tips': ['大多数款式都适合', '注意比例搭配', '突出优点', '保持整体协调']},
                    {'bodyType': 'curvy', 'name': '曲线型', 'tips': ['强调腰线', 'V 领延伸颈部线条', 'A 字裙摆', '避免过于宽松']},
                    {'bodyType': 'plus', 'name': '丰满型', 'tips': ['深色显瘦', '垂直线条', '适当露肤', '选择合适尺码']}
                ],
                'seasonalRules': [
                    {'season': 'spring', 'name': '春季', 'tips': ['薄外套必备', '浅色系', '透气面料', '应对温差']},
                    {'season': 'summer', 'name': '夏季', 'tips': ['清爽浅色系', '透气吸汗', '防晒', '简约清爽']},
                    {'season': 'autumn', 'name': '秋季', 'tips': ['暖色系', '层次穿搭', '薄毛衣', '风衣外套']},
                    {'season': 'winter', 'name': '冬季', 'tips': ['保暖优先', '深色系', '叠穿', '配饰保暖']}
                ]
            }
            self.rules_path.write_text(json.dumps(default_rules, indent=2, ensure_ascii=False))

        # 初始化示例穿搭库
        if not self.outfits_path.exists():
            sample_outfits = [
                {
                    'id': 'sample_001',
                    'name': '都市休闲风',
                    'style': 'casual',
                    'season': ['spring', 'autumn'],
                    'occasion': ['daily', 'travel'],
                    'description': '简约舒适的日常穿搭',
                    'items': ['白色 T 恤', '浅色牛仔裤', '休闲西装外套', '小白鞋'],
                    'colors': ['white', 'blue', 'gray'],
                    'imageUrl': None
                },
                {
                    'id': 'sample_002',
                    'name': '职场精英',
                    'style': 'formal',
                    'season': ['all'],
                    'occasion': ['work'],
                    'description': '专业得体的职场穿搭',
                    'items': ['白色衬衫', '黑色西裤', '修身西装', '皮鞋'],
                    'colors': ['white', 'black', 'navy'],
                    'imageUrl': None
                },
                {
                    'id': 'sample_003',
                    'name': '周末街头',
                    'style': 'street',
                    'season': ['spring', 'summer', 'autumn'],
                    'occasion': ['daily', 'party'],
                    'description': '潮流个性的街头风格',
                    'items': ['印花 T 恤', '工装裤', '棒球帽', '运动鞋'],
                    'colors': ['black', 'khaki', 'colorful'],
                    'imageUrl': None
                }
            ]
            self.outfits_path.write_text(json.dumps(sample_outfits, indent=2, ensure_ascii=False))

    def add_outfit_image(self, image_buffer: bytes, metadata: dict = None) -> dict:
        """
        添加穿搭图片到知识库

        Args:
            image_buffer: 图片二进制数据
            metadata: 元数据 {name, style, season, occasion, colors, description}

        Returns:
            添加的穿搭信息
        """
        metadata = metadata or {}
        outfit_id = str(uuid.uuid4())

        # 保存文件
        image_path = self.storage_path / 'images' / f'{outfit_id}.jpg'
        image_path.write_bytes(image_buffer)

        # 分析图片
        analysis = self._analyze_outfit_image(str(image_path))

        outfit = {
            'id': outfit_id,
            'name': metadata.get('name') or f'穿搭 {outfit_id[:8]}',
            'style': metadata.get('style') or analysis.get('style', 'casual'),
            'season': metadata.get('season') or analysis.get('season', ['spring']),
            'occasion': metadata.get('occasion') or analysis.get('occasion', ['daily']),
            'colors': metadata.get('colors') or analysis.get('colors', []),
            'description': metadata.get('description') or analysis.get('description', ''),
            'items': metadata.get('items') or analysis.get('items', []),
            'imageUrl': f'/data/knowledge/images/{outfit_id}.jpg',
            'tags': metadata.get('tags', []),
            'created_at': datetime.now().isoformat()
        }

        # 保存到库
        outfits = self.get_outfits()
        outfits.append(outfit)
        self.outfits_path.write_text(json.dumps(outfits, indent=2, ensure_ascii=False))

        return outfit

    def _analyze_outfit_image(self, image_path: str) -> dict:
        """分析穿搭图片"""
        if not self.dashscope_service:
            return {}

        prompt = """分析这张穿搭图片，提取以下信息并以 JSON 格式返回：
        - 风格（casual/formal/sporty/elegant/street/minimalist）
        - 适合季节（spring/summer/autumn/winter）
        - 适合场合（daily/work/party/date/travel）
        - 主要颜色
        - 服装单品列表
        - 穿搭描述

        只返回 JSON，不要其他文字。"""

        try:
            # 使用 DashScope VL 模型分析
            result = self.dashscope_service.analyze_garment(image_path)
            return result
        except Exception as e:
            print(f"分析图片失败：{e}")
            return {}

    def get_outfits(self, filters: dict = None) -> list:
        """
        获取所有穿搭知识

        Args:
            filters: 过滤条件 {style, season, occasion}

        Returns:
            穿搭列表
        """
        if not self.outfits_path.exists():
            return []

        outfits = json.loads(self.outfits_path.read_text())

        # 应用过滤
        if filters:
            if filters.get('style'):
                outfits = [o for o in outfits if o.get('style') == filters['style']]
            if filters.get('season'):
                outfits = [o for o in outfits if filters['season'] in o.get('season', [])]
            if filters.get('occasion'):
                outfits = [o for o in outfits if filters['occasion'] in o.get('occasion', [])]

        return outfits

    def get_rules(self) -> dict:
        """获取穿搭规则"""
        if not self.rules_path.exists():
            return {}
        return json.loads(self.rules_path.read_text())

    def match_outfits(self, garment: dict, preferences: dict = None) -> list:
        """
        匹配穿搭建议

        Args:
            garment: 服装特征 {style, colors, season, occasion}
            preferences: 用户偏好 {season, occasion}

        Returns:
            匹配的穿搭列表（按分数排序）
        """
        outfits = self.get_outfits()
        scored = []

        for outfit in outfits:
            score = 0
            reasons = []

            # 风格匹配
            if outfit.get('style') == garment.get('style'):
                score += 30
                reasons.append(f'风格一致：{outfit.get("style")}')

            # 季节匹配
            if preferences and preferences.get('season'):
                if preferences['season'] in outfit.get('season', []):
                    score += 20
                    reasons.append(f'适合{preferences["season"]}季节')

            # 场合匹配
            if preferences and preferences.get('occasion'):
                if preferences['occasion'] in outfit.get('occasion', []):
                    score += 20
                    reasons.append(f'适合{preferences["occasion"]}场合')

            # 颜色搭配
            color_score = self._calculate_color_match(garment.get('colors', []), outfit.get('colors', []))
            score += color_score
            if color_score >= 20:
                reasons.append('颜色搭配和谐')

            scored.append({
                **outfit,
                'score': score,
                'match_reason': '；'.join(reasons)
            })

        # 按分数排序
        return sorted(scored, key=lambda x: x['score'], reverse=True)

    def _calculate_color_match(self, garment_colors: list, outfit_colors: list) -> int:
        """计算颜色匹配度"""
        if not garment_colors or not outfit_colors:
            return 10

        # 兼容的颜色对
        compatible_pairs = [
            ['white', 'black'],
            ['white', 'blue'],
            ['black', 'gray'],
            ['blue', 'gray'],
            ['brown', 'beige'],
            ['green', 'khaki']
        ]

        for g_color in garment_colors:
            for o_color in outfit_colors:
                if g_color == o_color:
                    return 25  # 同色系
                if any(g_color in pair and o_color in pair for pair in compatible_pairs):
                    return 20

        return 10

    def delete_outfit(self, outfit_id: str) -> bool:
        """删除穿搭知识"""
        if not self.outfits_path.exists():
            return False

        outfits = json.loads(self.outfits_path.read_text())
        filtered = [o for o in outfits if o['id'] != outfit_id]

        if len(filtered) == len(outfits):
            return False

        self.outfits_path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False))

        # 删除图片
        image_path = self.storage_path / 'images' / f'{outfit_id}.jpg'
        if image_path.exists():
            image_path.unlink()

        return True

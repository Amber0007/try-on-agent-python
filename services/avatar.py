"""
数字人管理服务
管理人物动作、身材、肤色等状态
"""
import json
import uuid
import typing
from pathlib import Path
from datetime import datetime
from config import PATHS, AVATAR_CONFIG


class AvatarService:
    """数字人管理服务"""

    def __init__(self):
        self.storage_path = PATHS['avatars']
        self.config_path = self.storage_path / 'avatars.json'
        self._ensure_directories()
        self._init_default_avatars()

    def _ensure_directories(self):
        """确保目录存在"""
        (self.storage_path / 'base').mkdir(parents=True, exist_ok=True)
        (self.storage_path / 'generated').mkdir(parents=True, exist_ok=True)

    def _init_default_avatars(self):
        """初始化默认数字人预设"""
        if self.config_path.exists():
            return

        default_avatars = [
            # 身材类型 x 肤色 x 姿势的组合
            {'id': 'avatar_001', 'name': 'slim-fair-standing', 'bodyType': 'slim', 'skinTone': 'fair', 'pose': 'standing_front', 'gender': 'female'},
            {'id': 'avatar_002', 'name': 'slim-light-standing', 'bodyType': 'slim', 'skinTone': 'light', 'pose': 'standing_front', 'gender': 'female'},
            {'id': 'avatar_003', 'name': 'standard-fair-standing', 'bodyType': 'standard', 'skinTone': 'fair', 'pose': 'standing_front', 'gender': 'female'},
            {'id': 'avatar_004', 'name': 'standard-medium-standing', 'bodyType': 'standard', 'skinTone': 'medium', 'pose': 'standing_front', 'gender': 'female'},
            {'id': 'avatar_005', 'name': 'curvy-light-standing', 'bodyType': 'curvy', 'skinTone': 'light', 'pose': 'standing_front', 'gender': 'female'},
            {'id': 'avatar_006', 'name': 'plus-dark-standing', 'bodyType': 'plus', 'skinTone': 'dark', 'pose': 'standing_front', 'gender': 'female'},

            # 不同姿势
            {'id': 'avatar_007', 'name': 'slim-fair-side', 'bodyType': 'slim', 'skinTone': 'fair', 'pose': 'standing_side', 'gender': 'female'},
            {'id': 'avatar_008', 'name': 'slim-fair-sitting', 'bodyType': 'slim', 'skinTone': 'fair', 'pose': 'sitting', 'gender': 'female'},
            {'id': 'avatar_009', 'name': 'slim-fair-walking', 'bodyType': 'slim', 'skinTone': 'fair', 'pose': 'walking', 'gender': 'female'},

            # 男性模特
            {'id': 'avatar_010', 'name': 'male-standard-fair', 'bodyType': 'standard', 'skinTone': 'fair', 'pose': 'standing_front', 'gender': 'male'},
            {'id': 'avatar_011', 'name': 'male-slim-light', 'bodyType': 'slim', 'skinTone': 'light', 'pose': 'standing_front', 'gender': 'male'},
            {'id': 'avatar_012', 'name': 'male-curvy-medium', 'bodyType': 'curvy', 'skinTone': 'medium', 'pose': 'standing_front', 'gender': 'male'}
        ]

        # 保存预设配置
        self.config_path.write_text(json.dumps(default_avatars, indent=2, ensure_ascii=False))

        # 创建占位图片
        for avatar in default_avatars:
            image_path = self.storage_path / 'base' / f"{avatar['id']}.png"
            if not image_path.exists():
                self._create_placeholder_image(image_path, avatar)

    def _create_placeholder_image(self, image_path: Path, avatar: dict):
        """创建占位 SVG 图片"""
        colors = {
            'fair': '#FFE5D0',
            'light': '#F0D0B0',
            'medium': '#D0A080',
            'olive': '#C08060',
            'dark': '#805040'
        }

        svg = f"""<svg width="400" height="600" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="600" fill="#f5f5f5"/>
  <ellipse cx="200" cy="150" rx="80" ry="100" fill="{colors.get(avatar['skinTone'], '#F0D0B0')}"/>
  <rect x="150" y="250" width="100" height="300" fill="#ddd" rx="20"/>
  <text x="200" y="350" text-anchor="middle" font-size="16" fill="#666">{avatar['bodyType']}</text>
  <text x="200" y="380" text-anchor="middle" font-size="16" fill="#666">{avatar['pose']}</text>
  <text x="200" y="550" text-anchor="middle" font-size="14" fill="#999">{avatar['gender']} - {avatar['skinTone']}</text>
</svg>"""

        image_path.write_text(svg)

    def get_avatars(self, filters: dict = None) -> list:
        """
        获取所有可用的数字人

        Args:
            filters: 过滤条件 {gender, bodyType, skinTone, pose}

        Returns:
            数字人列表
        """
        avatars = json.loads(self.config_path.read_text())

        # 应用过滤
        if filters:
            if filters.get('gender'):
                avatars = [a for a in avatars if a['gender'] == filters['gender']]
            if filters.get('bodyType'):
                avatars = [a for a in avatars if a['bodyType'] == filters['bodyType']]
            if filters.get('skinTone'):
                avatars = [a for a in avatars if a['skinTone'] == filters['skinTone']]
            if filters.get('pose'):
                avatars = [a for a in avatars if a['pose'] == filters['pose']]

        # 添加图片 URL
        return [{
            **avatar,
            'imageUrl': f'/data/avatars/base/{avatar["id"]}.png',
            'thumbnailUrl': f'/data/avatars/base/{avatar["id"]}.png'
        } for avatar in avatars]

    def get_avatar(self, avatar_id: str) -> typing.Optional[dict]:
        """获取单个数字人详情"""
        avatars = json.loads(self.config_path.read_text())
        for avatar in avatars:
            if avatar['id'] == avatar_id:
                return {
                    **avatar,
                    'imageUrl': f'/data/avatars/base/{avatar_id}.png'
                }
        return None

    def create_avatar(self, options: dict) -> dict:
        """
        创建自定义数字人

        Args:
            options: 数字人配置 {name, gender, bodyType, skinTone, pose}

        Returns:
            创建的数字人信息
        """
        avatars = json.loads(self.config_path.read_text())

        new_avatar = {
            'id': f'avatar_{str(uuid.uuid4())[:8]}',
            'name': options.get('name', f'Custom-{options.get("bodyType", "standard")}-{options.get("skinTone", "light")}'),
            'bodyType': options.get('bodyType', 'standard'),
            'skinTone': options.get('skinTone', 'light'),
            'pose': options.get('pose', 'standing_front'),
            'gender': options.get('gender', 'female'),
            'custom': True
        }

        avatars.append(new_avatar)
        self.config_path.write_text(json.dumps(avatars, indent=2, ensure_ascii=False))

        # 创建图片
        image_path = self.storage_path / 'base' / f"{new_avatar['id']}.png"
        self._create_placeholder_image(image_path, new_avatar)

        return {
            **new_avatar,
            'imageUrl': f'/data/avatars/base/{new_avatar["id"]}.png'
        }

    def delete_avatar(self, avatar_id: str) -> bool:
        """删除数字人"""
        avatars = json.loads(self.config_path.read_text())
        filtered = [a for a in avatars if a['id'] != avatar_id]

        if len(filtered) == len(avatars):
            return False  # 未找到

        self.config_path.write_text(json.dumps(filtered, indent=2, ensure_ascii=False))

        # 删除图片
        image_path = self.storage_path / 'base' / f'{avatar_id}.png'
        if image_path.exists():
            image_path.unlink()

        return True

    def get_options(self) -> dict:
        """获取所有可用选项"""
        return {
            'bodyTypes': AVATAR_CONFIG['body_types'],
            'skinTones': AVATAR_CONFIG['skin_tones'],
            'poses': AVATAR_CONFIG['poses'],
            'genders': ['female', 'male']
        }

"""
服装图像处理服务
处理淘宝服装图片：下载、抠图、标准化
"""
import requests
import uuid
import typing
import json
from pathlib import Path
from datetime import datetime
from config import PATHS, DASHSCOPE_API_KEY, REMOVE_BG_API_KEY
from services.dashscope import DashScopeService


class OutfitService:
    """服装图像处理服务"""

    def __init__(self):
        self.storage_path = PATHS['outfits']
        self.dashscope_service = DashScopeService(DASHSCOPE_API_KEY) if DASHSCOPE_API_KEY else None
        self._ensure_directories()

    def _ensure_directories(self):
        """确保目录存在"""
        (self.storage_path / 'original').mkdir(parents=True, exist_ok=True)
        (self.storage_path / 'masked').mkdir(parents=True, exist_ok=True)

    def process_from_url(self, image_url: str) -> dict:
        """
        从 URL 下载并处理服装图片

        Args:
            image_url: 图片 URL

        Returns:
            处理后的图片信息
        """
        image_id = str(uuid.uuid4())

        # 1. 下载图片
        original_path = self._download_image(image_url, image_id)

        # 2. 去除背景获取服装
        masked_buffer = self._remove_background(original_path)

        # 3. 保存处理后的图片
        masked_path = self.storage_path / 'masked' / f'{image_id}.png'
        masked_path.write_bytes(masked_buffer)

        # 4. 分析服装特征
        attributes = self._analyze_garment(str(masked_path))

        return {
            'id': image_id,
            'original_path': str(original_path),
            'masked_path': str(masked_path),
            'masked_url': f'/data/outfits/masked/{image_id}.png',
            'attributes': attributes,
            'created_at': datetime.now().isoformat()
        }

    def process_from_buffer(self, image_buffer: bytes) -> dict:
        """
        处理上传的图片 Buffer

        Args:
            image_buffer: 图片二进制数据

        Returns:
            处理后的图片信息
        """
        image_id = str(uuid.uuid4())

        # 1. 保存原始图片
        original_path = self.storage_path / 'original' / f'{image_id}.jpg'
        original_path.write_bytes(image_buffer)

        # 2. 去除背景
        masked_buffer = self._remove_background(str(original_path))

        # 3. 保存处理后的图片
        masked_path = self.storage_path / 'masked' / f'{image_id}.png'
        masked_path.write_bytes(masked_buffer)

        # 4. 分析特征（简化处理）
        attributes = {
            'type': 'unknown',
            'color': 'unknown',
            'style': 'casual',
            'season': 'all',
            'occasion': 'daily'
        }

        return {
            'id': image_id,
            'masked_path': str(masked_path),
            'masked_url': f'/data/outfits/masked/{image_id}.png',
            'attributes': attributes,
            'created_at': datetime.now().isoformat()
        }

    def _download_image(self, url: str, image_id: str) -> Path:
        """下载图片"""
        response = requests.get(url)
        file_path = self.storage_path / 'original' / f'{image_id}.jpg'
        file_path.write_bytes(response.content)
        return file_path

    def _remove_background(self, image_path: str) -> bytes:
        """
        去除背景

        Args:
            image_path: 图片路径

        Returns:
            去背后的图片数据
        """
        if REMOVE_BG_API_KEY:
            # 使用 Remove.bg API
            return self._remove_bg_api(image_path)
        else:
            # 返回原图（建议配置 Remove.bg API）
            return Path(image_path).read_bytes()

    def _remove_bg_api(self, image_path: str) -> bytes:
        """调用 Remove.bg API"""
        with open(image_path, 'rb') as f:
            files = {'image_file': f}
            data = {'size': 'full'}
            headers = {'X-Api-Key': REMOVE_BG_API_KEY}

            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files=files,
                data=data,
                headers=headers
            )

            if response.status_code != 200:
                raise Exception(f"Remove.bg API 失败：{response.text}")

            return response.content

    def _analyze_garment(self, image_path: str) -> dict:
        """分析服装特征"""
        if self.dashscope_service:
            return self.dashscope_service.analyze_garment(image_path)
        return {
            'type': 'unknown',
            'color': 'unknown',
            'style': 'casual',
            'season': 'all',
            'occasion': 'daily'
        }

    def list_outfits(self) -> list:
        """获取已处理的服装列表"""
        masked_dir = self.storage_path / 'masked'
        if not masked_dir.exists():
            return []

        outfits = []
        for file_path in masked_dir.glob('*.png'):
            outfits.append({
                'id': file_path.stem,
                'masked_url': f'/data/outfits/masked/{file_path.name}',
                'masked_path': str(file_path.absolute()),  # 添加本地路径
                'created_at': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
            })
        return outfits

    def delete_outfit(self, outfit_id: str) -> bool:
        """删除服装图片"""
        paths = [
            self.storage_path / 'original' / f'{outfit_id}.jpg',
            self.storage_path / 'masked' / f'{outfit_id}.png'
        ]

        for path in paths:
            if path.exists():
                path.unlink()
        return True

    def get_outfit(self, outfit_id: str) -> typing.Optional[dict]:
        """获取单个服装信息"""
        masked_dir = self.storage_path / 'masked'
        file_path = masked_dir / f'{outfit_id}.png'

        if not file_path.exists():
            return None

        return {
            'id': outfit_id,
            'masked_url': f'/data/outfits/masked/{outfit_id}.png',
            'masked_path': str(file_path.absolute())
        }

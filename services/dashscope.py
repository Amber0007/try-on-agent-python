"""
阿里云 DashScope API 客户端
提供虚拟试衣和图像理解能力
"""
import requests
import base64
from pathlib import Path
from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_VTON_MODEL, DASHSCOPE_VL_MODEL


class DashScopeService:
    """阿里云 DashScope API 服务"""

    def __init__(self, api_key=None):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = DASHSCOPE_BASE_URL

    def virtual_try_on(self, garment_image: str, model_image: str) -> str:
        """
        虚拟试衣 - 将服装迁移到模特图

        Args:
            garment_image: 服装图片 URL 或文件路径
            model_image: 模特底图 URL 或文件路径

        Returns:
            生成结果的图片 URL
        """
        if not self.api_key:
            raise ValueError("DashScope API Key 未配置")

        # 准备图片数据
        garment_data = self._prepare_image(garment_image)
        model_data = self._prepare_image(model_image)

        # 构建请求
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }

        files = {
            'garment_image': ('garment.png', garment_data, 'image/png'),
            'model_image': ('model.png', model_data, 'image/png')
        }

        data = {
            'model': DASHSCOPE_VTON_MODEL,
            'prompt': 'high quality, realistic, professional photography'
        }

        # 发送请求
        url = f"{self.base_url}/services/aigc/virtual-try-on/generation"
        response = requests.post(url, headers=headers, files=files, data=data)

        if response.status_code != 200:
            raise Exception(f"API 请求失败：{response.text}")

        result = response.json()
        if result.get('output', {}).get('url'):
            return result['output']['url']

        raise Exception("API 返回数据中未找到结果 URL")

    def analyze_garment(self, image_path: str) -> dict:
        """
        分析服装图片特征

        Args:
            image_path: 图片路径或 URL

        Returns:
            服装特征描述
        """
        if not self.api_key:
            return self._get_default_analysis()

        prompt = """分析这张服装图片，提取以下信息并以 JSON 格式返回：
        - 服装类型（上衣/裤子/裙子/外套等）
        - 颜色
        - 风格（休闲/正式/运动等）
        - 适合季节
        - 适合场合
        - 材质推测
        - 设计特点

        只返回 JSON，不要其他文字。"""

        # 构建消息内容
        content = []
        if image_path.startswith('http'):
            content.append({'image': image_path})
        else:
            # 本地文件转为 base64
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            content.append({'image': f'data:image/png;base64,{image_base64}'})
        content.append({'text': prompt})

        payload = {
            'model': DASHSCOPE_VL_MODEL,
            'input': {
                'messages': [{
                    'role': 'user',
                    'content': content
                }]
            }
        }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/services/aigc/multimodal-generation"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"VL API 请求失败：{response.text}")
            return self._get_default_analysis()

        result = response.json()
        content = result.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', '')

        # 尝试解析 JSON
        import re
        import json
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {'description': content}

    def _prepare_image(self, image_src: str) -> bytes:
        """准备图片数据"""
        if image_src.startswith('http'):
            # 下载图片
            response = requests.get(image_src)
            return response.content
        else:
            # 读取本地文件
            with open(image_src, 'rb') as f:
                return f.read()

    def _get_default_analysis(self) -> dict:
        """返回默认分析结果"""
        return {
            'type': 'unknown',
            'color': 'unknown',
            'style': 'casual',
            'season': 'all',
            'occasion': 'daily'
        }

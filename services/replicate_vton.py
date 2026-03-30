"""
Replicate API 虚拟试衣服务
使用 IDM-VTON 或 OOTDiffusion 模型
通过 HTTP 直接调用 API，避免 replicate 库的兼容性问题
"""
import os
import requests
import base64
import time
import json
from pathlib import Path
from datetime import datetime


class ReplicateVTONService:
    """Replicate 虚拟试衣服务（HTTP 方式）"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('REPLICATE_API_KEY')
        if not self.api_key:
            raise ValueError("Replicate API Key 未配置")

        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # IDM-VTON 模型
        # 参考：https://replicate.com/yisol/idm-vton
        self.model = "yisol/idm-vton"
        self.version = "728c722133b8356f574c1f5cfa41581188c890ee3b3bb0c2e13e1cb2916d2a28"

    def virtual_try_on(self, garment_image: str, model_image: str) -> dict:
        """
        虚拟试衣 - 使用 IDM-VTON 模型

        Args:
            garment_image: 服装图片文件路径（已去背的服装）
            model_image: 模特底图文件路径

        Returns:
            生成结果的图片 URL 和信息
        """
        print(f"提交 Replicate 虚拟试衣任务...")
        print(f"Garment: {garment_image}")
        print(f"Model: {model_image}")

        try:
            # 将图片转换为 base64 数据 URL
            garment_data_url = self._encode_to_data_url(garment_image)
            model_data_url = self._encode_to_data_url(model_image)

            # 创建预测任务
            prediction = self._create_prediction(garment_data_url, model_data_url)

            if not prediction:
                return {
                    'success': False,
                    'error': '无法创建预测任务'
                }

            # 轮询获取结果
            result_url = self._wait_for_prediction(prediction['id'])

            if result_url:
                return {
                    'success': True,
                    'imageUrl': result_url,
                    'type': 'virtual_try_on',
                    'provider': 'replicate',
                    'model': 'IDM-VTON',
                    'created_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': '任务执行失败'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"Replicate API 错误：{str(e)}",
                'provider': 'replicate'
            }

    def _encode_to_data_url(self, image_path: str) -> str:
        """将图片转换为 data URL"""
        from PIL import Image

        # 检测 MIME 类型
        ext = Path(image_path).suffix.lower()
        if ext == '.svg' or self._is_svg_file(image_path):
            mime_type = 'svg+xml'
        else:
            try:
                with Image.open(image_path) as img:
                    format_map = {'JPEG': 'jpeg', 'PNG': 'png', 'WEBP': 'webp'}
                    mime_type = format_map.get(img.format, 'jpeg')
            except:
                mime_type = 'jpeg'

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        return f"data:image/{mime_type};base64,{image_data}"

    def _is_svg_file(self, image_path: str) -> bool:
        """检查文件是否是 SVG 格式"""
        try:
            with open(image_path, 'rb') as f:
                header = f.read(100)
                return b'<svg' in header
        except Exception:
            return False

    def _create_prediction(self, garment_data_url: str, model_data_url: str) -> dict:
        """创建预测任务"""
        url = f"{self.base_url}/predictions"

        payload = {
            "version": self.version,
            "input": {
                "clothes": garment_data_url,
                "image": model_data_url,
                "crop": True,
                "seed": 42,
            }
        }

        print(f"创建预测任务：{url}")
        response = requests.post(url, headers=self.headers, json=payload)
        print(f"响应状态：{response.status_code}")
        print(f"响应内容：{response.text[:500]}")

        if response.status_code not in [200, 201]:
            raise Exception(f"创建任务失败：{response.status_code} - {response.text}")

        return response.json()

    def _wait_for_prediction(self, prediction_id: str, max_attempts: int = 120) -> str:
        """轮询预测结果"""
        url = f"{self.base_url}/predictions/{prediction_id}"

        print(f"等待任务完成 (ID: {prediction_id})...")

        for i in range(max_attempts):
            time.sleep(2)  # 每 2 秒查询一次

            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"查询失败：{response.status_code}")
                continue

            result = response.json()
            status = result.get('status', '')

            if i % 5 == 0:  # 每 5 次打印一次状态
                print(f"任务状态：{status} (第 {i+1} 次查询)")

            if status == 'succeeded':
                # 返回输出图片 URL
                output = result.get('output', [])
                if output and len(output) > 0:
                    return output[0]
                return None
            elif status in ['failed', 'canceled']:
                error_msg = result.get('error', '未知错误')
                print(f"任务失败：{error_msg}")
                return None

        print("任务超时")
        return None


# 备选模型：OOTDiffusion
class OOTDiffusionService:
    """OOTDiffusion 虚拟试衣服务（备选）"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('REPLICATE_API_KEY')
        if not self.api_key:
            raise ValueError("Replicate API Key 未配置")

        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # OOTDiffusion 模型版本
        self.model = "levihsu/oot-diffusion"
        self.version = "5114d9167d4a4dc4beb020326849642e762409dc"  # 示例版本

    def virtual_try_on(self, garment_image: str, model_image: str) -> dict:
        """使用 OOTDiffusion 进行虚拟试衣"""
        try:
            garment_data_url = self._encode_to_data_url(garment_image)
            model_data_url = self._encode_to_data_url(model_image)

            url = f"{self.base_url}/predictions"
            payload = {
                "version": self.version,
                "input": {
                    "garm_img": garment_data_url,
                    "person_img": model_data_url,
                    "crop": True,
                }
            }

            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code not in [200, 201]:
                return {
                    'success': False,
                    'error': f"创建任务失败：{response.status_code}"
                }

            prediction = response.json()
            result_url = self._wait_for_prediction(prediction['id'])

            if result_url:
                return {
                    'success': True,
                    'imageUrl': result_url,
                    'type': 'virtual_try_on',
                    'provider': 'replicate',
                    'model': 'OOTDiffusion',
                    'created_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': '任务执行失败'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f"OOTDiffusion API 错误：{str(e)}",
                'provider': 'replicate'
            }

    def _encode_to_data_url(self, image_path: str) -> str:
        """将图片转换为 data URL"""
        from PIL import Image
        ext = Path(image_path).suffix.lower()
        if ext == '.svg':
            mime_type = 'svg+xml'
        else:
            try:
                with Image.open(image_path) as img:
                    format_map = {'JPEG': 'jpeg', 'PNG': 'png', 'WEBP': 'webp'}
                    mime_type = format_map.get(img.format, 'jpeg')
            except:
                mime_type = 'jpeg'

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{mime_type};base64,{image_data}"

    def _wait_for_prediction(self, prediction_id: str, max_attempts: int = 120) -> str:
        """轮询预测结果"""
        url = f"{self.base_url}/predictions/{prediction_id}"

        for i in range(max_attempts):
            time.sleep(2)

            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                continue

            result = response.json()
            status = result.get('status', '')

            if status == 'succeeded':
                output = result.get('output', [])
                if output and len(output) > 0:
                    return output[0]
                return None
            elif status in ['failed', 'canceled']:
                return None

        return None

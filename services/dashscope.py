"""
阿里云 DashScope API 客户端
提供虚拟试衣和图像理解能力
"""
import dashscope
import requests
import base64
import time
import json
from pathlib import Path
from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_VTON_MODEL, DASHSCOPE_VL_MODEL


class DashScopeService:
    """阿里云 DashScope API 服务"""

    def __init__(self, api_key=None):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = DASHSCOPE_BASE_URL
        # 配置 SDK 的 API key
        dashscope.api_key = self.api_key

    def virtual_try_on(self, garment_image: str, model_image: str) -> str:
        """
        虚拟试衣 - 将服装迁移到模特图

        Args:
            garment_image: 服装图片文件路径
            model_image: 模特底图文件路径

        Returns:
            生成结果的图片 URL
        """
        if not self.api_key:
            raise ValueError("DashScope API Key 未配置")

        print(f"提交虚拟试衣任务...")
        print(f"Garment: {garment_image}")
        print(f"Model: {model_image}")

        # 将图片编码为 base64
        garment_base64 = self._encode_image(garment_image)
        model_base64 = self._encode_image(model_image)

        # 使用 dashscope SDK 调用
        from dashscope import Generation

        prompt = """将这件服装穿到模特身上，保持服装的细节和颜色不变。
        输出高质量的虚拟试衣结果图片。"""

        # 构造多模态输入 - 使用 base64 格式
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": model_base64},
                    {"image": garment_base64},
                    {"text": prompt}
                ]
            }
        ]

        # 尝试使用 qwen-vl-max 进行图像处理和生成
        response = Generation.call(
            model="qwen-vl-max",
            messages=messages
        )

        print(f"SDK 响应：{response}")

        if response.status_code == 200:
            result = response.output.choices[0].message.content
            print(f"生成结果：{result}")
            # 如果返回的是文本，提取图片 URL
            import re
            img_match = re.search(r'!\[.*?\]\((https?://.*?)\)', result)
            if img_match:
                return img_match.group(1)
            # 如果返回的是图片对象
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and 'image' in item:
                        return item['image']
            return str(result)
        else:
            raise Exception(f"API 请求失败：{response.code} - {response.message}")

    def _virtual_try_on_http(self, garment_image: str, model_image: str) -> str:
        """HTTP 方式调用虚拟试衣 API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # 将本地路径转换为 file:// URL
        garment_path = Path(garment_image).absolute()
        model_path = Path(model_image).absolute()

        input_data = {
            "ref_image": f"file://{garment_path}",
            "cloth_image": f"file://{model_path}"
        }

        # 通义万相虚拟试衣 endpoint - 使用生成式模型 API
        task_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/generation"
        payload = {
            "model": DASHSCOPE_VTON_MODEL,
            "input": input_data
        }

        print(f"HTTP 方式提交虚拟试衣任务...")
        print(f"URL: {task_url}")
        print(f"Garment: {garment_path}")
        print(f"Model: {model_path}")

        response = requests.post(task_url, headers=headers, json=payload)
        print(f"提交响应：{response.status_code}")
        print(f"响应内容：{response.text[:500]}")

        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"API 请求失败：{error_data.get('message', response.text)}")

        result = response.json()
        print(f"完整响应：{json.dumps(result, indent=2)[:1000]}")

        # 检查是否是同步返回结果
        if result.get('output', {}).get('image_url'):
            return result['output']['image_url']

        # 异步任务需要轮询
        task_id = result.get('output', {}).get('task_id')
        if not task_id:
            raise Exception(f"未获取到任务 ID: {result}")

        # 轮询任务状态
        return self._poll_task_status(task_id, headers)

    def _poll_task_status(self, task_id: str, headers: dict, max_attempts: int = 60) -> str:
        """轮询异步任务状态"""
        task_url = f"{self.base_url}/tasks/{task_id}"

        for i in range(max_attempts):
            time.sleep(2)  # 每 2 秒查询一次

            response = requests.get(task_url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"查询任务失败：{response.text}")

            result = response.json()
            task_status = result.get('output', {}).get('task_status', '')

            print(f"任务状态：{task_status} (第 {i+1} 次查询)")

            if task_status == 'SUCCEEDED':
                # 返回视频或图片 URL
                output = result.get('output', {})
                return output.get('video_url') or output.get('image_url') or output.get('results', [{}])[0].get('url', '')
            elif task_status in ['FAILED', 'CANCELLED']:
                raise Exception(f"任务失败：{result.get('output', {}).get('message', '未知错误')}")

        raise Exception("任务超时")

    def _encode_image(self, image_path: str) -> str:
        """将图片编码为 base64"""
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/png;base64,{image_data}"

    def analyze_garment(self, image_path: str) -> dict:
        """
        分析服装图片特征
        使用 qwen3.5-flash 模型

        Args:
            image_path: 图片路径

        Returns:
            服装特征描述
        """
        if not self.api_key:
            return self._get_default_analysis()

        prompt = """分析这张服装图片，提取以下信息并以 JSON 格式返回：
        - 服装类型（上衣/裤子/裙子/外套等）
        - 颜色
        - 风格（casual/formal/sporty/elegant/street/minimalist）
        - 适合季节（spring/summer/autumn/winter）
        - 适合场合（daily/work/party/date/travel）

        只返回 JSON，不要其他文字。"""

        # 使用 file:// 格式
        payload = {
            "model": DASHSCOPE_VL_MODEL,
            "input": {
                "messages": [{
                    "role": "user",
                    "content": [
                        {"image": f"file://{image_path}"},
                        {"text": prompt}
                    ]
                }]
            }
        }

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 使用正确的 endpoint
        url = f"{self.base_url}/services/aigc/multimodal-generation/generation"
        print(f"调用 VL 模型：{url}")

        response = requests.post(url, headers=headers, json=payload)
        print(f"VL API 响应：{response.status_code}")

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

    def _get_default_analysis(self) -> dict:
        """返回默认分析结果"""
        return {
            'type': 'unknown',
            'color': 'unknown',
            'style': 'casual',
            'season': 'all',
            'occasion': 'daily'
        }

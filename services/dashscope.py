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

    def virtual_try_on(self, garment_image: str, model_image: str) -> dict:
        """
        虚拟试衣 - 分析服装搭配效果

        Args:
            garment_image: 服装图片文件路径（已去背的服装）
            model_image: 模特底图文件路径

        Returns:
            分析结果和穿搭建议
        """
        if not self.api_key:
            raise ValueError("DashScope API Key 未配置")

        # 检查图片格式，SVG 格式不被支持
        if self._is_svg_file(model_image):
            raise Exception("数字人图片是 SVG 格式，不被 DashScope API 支持。请使用 PNG 或 JPEG 格式的真实人像图片。")
        if self._is_svg_file(garment_image):
            raise Exception("服装图片是 SVG 格式，不被 DashScope API 支持。请使用 PNG 或 JPEG 格式的图片。")

        print(f"分析服装搭配效果...")
        print(f"Garment: {garment_image}")
        print(f"Model: {model_image}")

        # 将图片编码为 base64
        garment_base64 = self._encode_image(garment_image)
        model_base64 = self._encode_image(model_image)

        # 使用 qwen3.5-plus 多模态模型进行分析
        from dashscope import MultiModalConversation

        prompt = """请分析这张服装穿在模特身上的效果：
1. 描述服装的款式、颜色、材质特点
2. 分析服装与模特身形、肤色的搭配效果
3. 给出穿搭建议（适合的场合、季节、配饰建议）
4. 如果要使用 AI 绘图工具生成试衣效果，请提供英文 prompt

请以 JSON 格式返回，包含以下字段：
- style_description: 服装风格描述
- color_analysis: 色彩分析
- fit_analysis: 版型与身形匹配度
- occasion_suggestions: 适合场合列表
- season_suggestions: 适合季节列表
- ai_prompt: AI 绘图用的英文提示词"""

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

        response = MultiModalConversation.call(
            model="qwen3.5-plus",
            messages=messages
        )

        print(f"分析完成")

        if response.status_code == 200:
            result_text = response.output.choices[0].message.content[0]['text']
            print(f"分析结果：{result_text[:500]}...")
            return {
                'success': True,
                'analysis': result_text,
                'type': 'fashion_analysis'
            }
        else:
            raise Exception(f"API 请求失败：{response.code} - {response.message}")

    def _wanx_virtual_try_on(self, garment_image: str, model_image: str) -> str:
        """使用 Wanx 虚拟试衣 API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # 使用 file:// 格式传递本地图片
        garment_path = Path(garment_image).absolute()
        model_path = Path(model_image).absolute()

        # 通义万相虚拟试衣 API
        # 文档：https://help.aliyun.com/zh/dashscope/developer-reference/virtual-try-on
        task_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/virtual-try-on"
        payload = {
            "model": "wanx-virtual-try-on-turbo-v1",
            "input": {
                "person_img": f"file://{model_path}",
                "cloth_img": f"file://{garment_path}"
            },
            "parameters": {
                "size": "1024*1024"
            }
        }

        print(f"提交到：{task_url}")
        print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)[:500]}")

        response = requests.post(task_url, headers=headers, json=payload)
        print(f"提交响应：{response.status_code}")
        print(f"响应内容：{response.text[:1000]}")

        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"API 请求失败：{error_data.get('message', response.text)}")

        result = response.json()
        print(f"完整响应：{json.dumps(result, indent=2)[:1000]}")

        # 检查任务状态
        task_id = result.get('output', {}).get('task_id')
        if not task_id:
            # 可能是同步返回
            if result.get('output', {}).get('image_url'):
                return result['output']['image_url']
            raise Exception(f"未获取到任务 ID: {result}")

        # 轮询任务状态
        return self._poll_task_status(task_id, headers)

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
        """将图片编码为 base64，根据文件实际内容检测 MIME 类型"""
        from PIL import Image

        # 先检查是否是 SVG 文件（Pillow 不支持 SVG）
        ext = Path(image_path).suffix.lower()
        if ext == '.svg' or self._is_svg_file(image_path):
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/svg+xml;base64,{image_data}"

        # 使用 Pillow 检测真实图片格式
        try:
            with Image.open(image_path) as img:
                format_map = {
                    'JPEG': 'jpeg',
                    'PNG': 'png',
                    'GIF': 'gif',
                    'WEBP': 'webp',
                    'BMP': 'bmp'
                }
                image_format = format_map.get(img.format, 'jpeg')
        except Exception:
            # 如果 Pillow 无法识别，根据扩展名回退
            image_format = self._get_mime_from_extension(image_path)

        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/{image_format};base64,{image_data}"

    def _is_svg_file(self, image_path: str) -> bool:
        """检查文件是否是 SVG 格式"""
        try:
            with open(image_path, 'rb') as f:
                header = f.read(100)
                return b'<svg' in header
        except Exception:
            return False

    def _get_mime_from_extension(self, image_path: str) -> str:
        """根据文件扩展名获取 MIME 类型（回退方法）"""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.png': 'png',
            '.gif': 'gif',
            '.webp': 'webp',
            '.svg': 'svg+xml'
        }
        return mime_map.get(ext, 'jpeg')

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
            'Authorization': f'Bearer {self.api_key}',
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

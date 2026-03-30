"""
AI 虚拟试衣 Agent - Python 版
主程序（Flask 服务器）
"""
import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from config import PATHS, ensure_data_directories
from services.outfit import OutfitService
from services.avatar import AvatarService
from services.knowledge import KnowledgeService
from services.dashscope import DashScopeService
from services.replicate_vton import ReplicateVTONService

# 加载环境变量
load_dotenv()

# 初始化 Flask 应用
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB 限制
CORS(app)

# 确保数据目录存在
ensure_data_directories()

# 初始化服务
outfit_service = OutfitService()
avatar_service = AvatarService()
knowledge_service = KnowledgeService()


# ============ 页面路由 ============

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


# ============ API 路由 ============

@app.route('/api/status')
def status():
    """服务状态检查"""
    return jsonify({
        'apiConfigured': bool(os.getenv('DASHSCOPE_API_KEY')),
        'tryOnService': {
            'available': bool(os.getenv('DASHSCOPE_API_KEY')),
            'reason': 'OK' if os.getenv('DASHSCOPE_API_KEY') else 'API key not configured'
        }
    })


# ---- 虚拟试衣 ----

@app.route('/api/try-on', methods=['POST'])
def try_on():
    """执行虚拟试衣"""
    data = request.json
    outfit_id = data.get('outfitId')
    avatar_id = data.get('avatarId')
    mode = data.get('mode', 'analysis')  # 'analysis' 或 'generate'

    if not outfit_id or not avatar_id:
        return jsonify({'error': '缺少 outfitId 或 avatarId'}), 400

    # 获取服装信息
    outfit = outfit_service.get_outfit(outfit_id)
    if not outfit:
        return jsonify({'error': '未找到指定的服装'}), 404

    # 获取数字人信息
    avatar = avatar_service.get_avatar(avatar_id)
    if not avatar:
        return jsonify({'error': '未找到指定的数字人'}), 404

    # 准备图片路径
    garment_path = outfit['masked_path']
    model_path = avatar['imageUrl'].replace('/data/avatars', str(PATHS['avatars']))

    # 根据模式选择服务
    if mode == 'generate':
        # 模式 1：使用 Replicate 生成真实试衣图片
        replicate_key = os.getenv('REPLICATE_API_KEY')
        if not replicate_key:
            return jsonify({
                'success': False,
                'error': 'REPLICATE_API_KEY 未配置',
                'message': '请在 Replicate (https://replicate.com) 获取 API key，或切换到 analysis 模式'
            }), 503

        try:
            vton_service = ReplicateVTONService(replicate_key)
            result = vton_service.virtual_try_on(garment_path, model_path)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    else:
        # 模式 2（默认）：使用 DashScope 进行穿搭分析
        dashscope_key = os.getenv('DASHSCOPE_API_KEY')
        if not dashscope_key:
            return jsonify({
                'success': False,
                'error': 'DashScope API Key 未配置',
                'fallback': {
                    'message': '请配置 DASHSCOPE_API_KEY 后使用虚拟试衣功能',
                    'debug': {
                        'outfit_path': outfit.get('masked_path'),
                        'avatar_path': avatar.get('imageUrl')
                    }
                }
            }), 503

        try:
            dashscope = DashScopeService(dashscope_key)
            result = dashscope.virtual_try_on(garment_path, model_path)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# ---- 服装管理 ----

@app.route('/api/outfits', methods=['GET'])
def list_outfits():
    """获取服装列表"""
    outfits = outfit_service.list_outfits()
    return jsonify(outfits)


@app.route('/api/outfits/upload', methods=['POST'])
def upload_outfit():
    """上传服装图片"""
    if 'image' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    # 读取文件数据
    image_buffer = file.read()

    # 处理图片
    result = outfit_service.process_from_buffer(image_buffer)
    return jsonify(result)


@app.route('/api/outfits/url', methods=['POST'])
def process_outfit_url():
    """从 URL 处理服装图片"""
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': '缺少图片 URL'}), 400

    try:
        result = outfit_service.process_from_url(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/outfits/<outfit_id>', methods=['DELETE'])
def delete_outfit(outfit_id):
    """删除服装"""
    outfit_service.delete_outfit(outfit_id)
    return jsonify({'success': True})


# ---- 数字人管理 ----

@app.route('/api/avatars', methods=['GET'])
def list_avatars():
    """获取数字人列表"""
    filters = {
        'gender': request.args.get('gender'),
        'bodyType': request.args.get('bodyType'),
        'skinTone': request.args.get('skinTone'),
        'pose': request.args.get('pose')
    }
    # 移除空值
    filters = {k: v for k, v in filters.items() if v}

    avatars = avatar_service.get_avatars(filters)
    return jsonify(avatars)


@app.route('/api/avatars/options', methods=['GET'])
def get_avatar_options():
    """获取数字人选项"""
    return jsonify(avatar_service.get_options())


@app.route('/api/avatars', methods=['POST'])
def create_avatar():
    """创建数字人"""
    data = request.json
    avatar = avatar_service.create_avatar(data)
    return jsonify(avatar)


@app.route('/api/avatars/<avatar_id>', methods=['DELETE'])
def delete_avatar(avatar_id):
    """删除数字人"""
    if not avatar_service.delete_avatar(avatar_id):
        return jsonify({'error': '未找到数字人'}), 404
    return jsonify({'success': True})


# ---- 穿搭知识库 ----

@app.route('/api/knowledge', methods=['GET'])
def list_knowledge():
    """获取穿搭知识列表"""
    filters = {
        'style': request.args.get('style'),
        'season': request.args.get('season'),
        'occasion': request.args.get('occasion')
    }
    filters = {k: v for k, v in filters.items() if v}

    outfits = knowledge_service.get_outfits(filters)
    return jsonify(outfits)


@app.route('/api/knowledge', methods=['POST'])
def add_knowledge():
    """添加穿搭知识"""
    if 'image' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['image']
    image_buffer = file.read()

    # 收集元数据
    metadata = {
        'name': request.form.get('name'),
        'style': request.form.get('style'),
        'description': request.form.get('description'),
        'season': json.loads(request.form.get('season', '[]')),
        'occasion': json.loads(request.form.get('occasion', '[]')),
        'colors': json.loads(request.form.get('colors', '[]')),
        'tags': json.loads(request.form.get('tags', '[]'))
    }

    outfit = knowledge_service.add_outfit_image(image_buffer, metadata)
    return jsonify(outfit)


@app.route('/api/knowledge/rules', methods=['GET'])
def get_rules():
    """获取穿搭规则"""
    return jsonify(knowledge_service.get_rules())


@app.route('/api/knowledge/match', methods=['POST'])
def match_knowledge():
    """匹配穿搭建议"""
    data = request.json
    outfit_id = data.get('outfitId')
    preferences = data.get('preferences', {})

    if not outfit_id:
        return jsonify({'error': '缺少 outfitId'}), 400

    # 获取服装信息
    outfit = outfit_service.get_outfit(outfit_id)
    if not outfit:
        return jsonify({'error': '未找到指定的服装'}), 404

    # 匹配穿搭
    matches = knowledge_service.match_outfits(
        {
            'style': outfit.get('attributes', {}).get('style'),
            'colors': outfit.get('attributes', {}).get('colors'),
            'season': outfit.get('attributes', {}).get('season'),
            'occasion': outfit.get('attributes', {}).get('occasion')
        },
        preferences
    )

    return jsonify({
        'outfit': outfit,
        'recommendations': matches[:5],
        'rules': knowledge_service.get_rules()
    })


@app.route('/api/knowledge/<outfit_id>', methods=['DELETE'])
def delete_knowledge(outfit_id):
    """删除穿搭知识"""
    if not knowledge_service.delete_outfit(outfit_id):
        return jsonify({'error': '未找到穿搭'}), 404
    return jsonify({'success': True})


# ---- 静态文件服务 ----

@app.route('/data/<path:filepath>')
def serve_data(filepath):
    """服务数据目录下的文件"""
    return send_from_directory(PATHS['outfits'].parent, filepath)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

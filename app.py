#!/usr/bin/env python3
"""
Flask后端API - 图片处理服务
提供API接口供前端调用，处理图片并返回生成的图片
同时调用通义万相和TT API两个模型进行对比
"""

import os
import base64
import asyncio
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from function import get_function, get_system_prompt, combine_prompts
from UserPrompt_enhancer import OllamaPromptEnhancer
from wanx_api import call_wanx_api
from doubao_api import call_doubao_api

# 尝试导入PIL用于图片格式转换
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[警告] PIL/Pillow未安装，无法进行图片格式转换。建议安装: pip install Pillow")

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 确保 Save_picture 目录存在
SAVE_DIR = Path("Save_picture")
SAVE_DIR.mkdir(exist_ok=True)

# 临时图片目录（用于豆包API）
TEMP_IMAGE_DIR = Path("temp_images")
TEMP_IMAGE_DIR.mkdir(exist_ok=True)


async def call_both_apis(image_urls, prompt_text):
    """
    同时调用通义万相和豆包API两个API生成图片
    
    Args:
        image_urls: 输入图片列表（base64 data URL格式）
        prompt_text: 提示词文本
    
    Returns:
        dict: 包含两个模型结果的字典
            {
                'wanx': {'images': [...], 'error': None},
                'doubao': {'images': [...], 'error': None}
            }
    """
    print(f"\n{'='*60}")
    print("开始同时调用两个模型生成图片...")
    print(f"提示词: {prompt_text[:100]}...")
    print(f"{'='*60}\n")
    
    # 豆包API现在支持直接使用base64格式，无需转换为URL
    # 同时调用两个API
    wanx_result, doubao_result = await asyncio.gather(
        call_wanx_api(image_urls, prompt_text),  # 通义万相使用base64
        call_doubao_api(image_urls, prompt_text),  # 豆包API也直接使用base64
        return_exceptions=True
    )
    
    # 处理通义万相结果
    wanx_images = None
    wanx_error = None
    if isinstance(wanx_result, Exception):
        wanx_error = str(wanx_result)
        print(f"[通义万相] 调用异常: {wanx_error}")
    else:
        wanx_images, wanx_error = wanx_result
        if wanx_images:
            print(f"[通义万相] 成功生成 {len(wanx_images)} 张图片")
        else:
            print(f"[通义万相] 生成失败: {wanx_error}")
    
    # 处理豆包API结果
    doubao_images = None
    doubao_error = None
    if isinstance(doubao_result, Exception):
        doubao_error = str(doubao_result)
        print(f"[豆包API] 调用异常: {doubao_error}")
    else:
        doubao_images, doubao_error = doubao_result
        if doubao_images:
            print(f"[豆包API] 成功生成 {len(doubao_images)} 张图片")
        else:
            print(f"[豆包API] 生成失败: {doubao_error}")
    
    print(f"\n{'='*60}")
    print("两个模型调用完成")
    print(f"{'='*60}\n")
    
    return {
        'wanx': {
            'images': wanx_images or [],
            'error': wanx_error
        },
        'doubao': {
            'images': doubao_images or [],
            'error': doubao_error
        }
    }




@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory('.', 'index.html')


@app.route('/temp_images/<filename>')
def serve_temp_image(filename):
    """提供临时图片访问（用于豆包API）"""
    filepath = TEMP_IMAGE_DIR / filename
    if not filepath.exists():
        return "File not found", 404
    
    # 根据文件扩展名设置正确的Content-Type
    ext = filename.lower().split('.')[-1]
    mimetype_map = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    mimetype = mimetype_map.get(ext, 'application/octet-stream')
    
    # 设置CORS头，允许外部访问
    response = send_from_directory(str(TEMP_IMAGE_DIR), filename, mimetype=mimetype)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    
    return response


def save_temp_image_from_base64(image_data):
    """
    将base64图片保存为临时文件，返回可访问的URL
    
    Args:
        image_data: base64格式的图片数据（data URL格式）
    
    Returns:
        str: 图片的HTTP URL，如果失败返回None
    """
    try:
        # 处理data URL格式
        if image_data.startswith('data:image'):
            header, encoded = image_data.split(',', 1)
            image_format = header.split('/')[1].split(';')[0]
        else:
            encoded = image_data
            image_format = 'png'
        
        # 解码base64数据
        image_bytes = base64.b64decode(encoded)
        
        # 尝试将图片转换为PNG格式（TT API可能更支持PNG）
        # 如果转换失败，使用原始格式
        final_format = 'png'  # 统一使用PNG格式
        final_image_bytes = image_bytes
        
        if HAS_PIL:
            try:
                # 使用PIL打开图片并转换为PNG
                img = Image.open(io.BytesIO(image_bytes))
                # 如果是RGBA模式，保持；如果是其他模式，转换为RGB
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 保持透明度
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 转换为PNG格式的字节流
                png_buffer = io.BytesIO()
                img.save(png_buffer, format='PNG', optimize=True)
                final_image_bytes = png_buffer.getvalue()
                print(f"[临时图片] 已将图片从 {image_format} 转换为 PNG (原始: {len(image_bytes)} bytes, PNG: {len(final_image_bytes)} bytes)")
            except Exception as e:
                print(f"[临时图片] 图片格式转换失败，使用原始格式: {str(e)}")
                final_format = image_format
                final_image_bytes = image_bytes
        else:
            # 如果没有PIL，尝试使用原始格式，但如果格式不是PNG或JPG，强制使用PNG扩展名
            if image_format.lower() not in ('png', 'jpg', 'jpeg'):
                print(f"[临时图片] 警告: 图片格式 {image_format} 可能不被TT API支持，但无法转换（PIL未安装）")
                final_format = 'png'  # 至少使用PNG扩展名
            else:
                final_format = image_format
        
        # 生成唯一文件名（统一使用PNG扩展名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"temp_{timestamp}.{final_format}"
        filepath = TEMP_IMAGE_DIR / filename
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(final_image_bytes)
        
        # 返回可访问的URL
        # 使用Flask的URL生成（在请求上下文中）
        try:
            from flask import url_for, request
            image_url = url_for('serve_temp_image', filename=filename, _external=True)
            print(f"[临时图片] 使用Flask外部URL: {image_url}")
        except RuntimeError:
            # 不在请求上下文中，直接构造URL
            try:
                base_url = request.host_url.rstrip('/')
            except:
                base_url = "http://localhost:5000"  # 默认值
            image_url = f"{base_url}/temp_images/{filename}"
            print(f"[临时图片] 使用本地URL: {image_url}")
        
        return image_url
    except Exception as e:
        print(f"保存临时图片失败: {str(e)}")
        return None


def save_image_from_base64(image_data, function_id):
    """
    将base64图片数据保存到文件
    
    Args:
        image_data: base64格式的图片数据（可以是data URL格式）
        function_id: 功能ID，用于命名文件（可能包含模型标识，如 function_id_wanx）
    
    Returns:
        str: 保存的文件路径
    """
    try:
        # 处理data URL格式
        if image_data.startswith('data:image'):
            # 提取base64数据部分
            header, encoded = image_data.split(',', 1)
            # 从header中提取图片格式
            image_format = header.split('/')[1].split(';')[0]
        else:
            # 直接是base64字符串
            encoded = image_data
            image_format = 'png'
        
        # 解码base64数据
        image_bytes = base64.b64decode(encoded)
        
        # 生成文件名：功能名_模型_时间戳.扩展名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
        
        # 解析function_id，可能包含模型标识
        if '_wanx' in function_id:
            base_function_id = function_id.replace('_wanx', '')
            model_suffix = '_WanX'
        elif '_doubao' in function_id:
            base_function_id = function_id.replace('_doubao', '')
            model_suffix = '_Doubao'
        else:
            base_function_id = function_id
            model_suffix = ''
        
        function_name = get_function(base_function_id).get('name_en', base_function_id) if get_function(base_function_id) else base_function_id
        filename = f"{function_name}{model_suffix}_{timestamp}.{image_format}"
        filepath = SAVE_DIR / filename
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        return str(filepath)
    except Exception as e:
        print(f"保存图片失败: {str(e)}")
        return None


@app.route('/api/process', methods=['POST'])
def process_images():
    """处理图片的API端点"""
    try:
        # 检查请求数据
        if 'function' not in request.form:
            return jsonify({"error": "缺少function参数"}), 400
        
        function_id = request.form['function']
        
        # 验证功能ID是否有效
        function_config = get_function(function_id)
        if not function_config:
            return jsonify({"error": f"无效的功能ID: {function_id}"}), 400
        
        # 获取系统提示词
        system_prompt = get_system_prompt(function_id)
        if not system_prompt:
            return jsonify({"error": "无法获取系统提示词"}), 500
        
        # 获取用户提示词（可选）
        user_prompt = request.form.get('prompt', '').strip()
        
        # 获取是否启用提示词增强（默认为启用）
        enable_enhance = request.form.get('enable_rag', '1').strip() == '1'
        
        # 根据用户选择决定是否使用提示词增强
        if enable_enhance and user_prompt:
            # 使用DeepSeek-R1模型增强用户提示词
            print(f"\n{'='*60}")
            print("开始使用DeepSeek-R1模型增强提示词...")
            print(f"原始提示词: {user_prompt}")
            print(f"{'='*60}\n")
            
            enhancer = OllamaPromptEnhancer()
            # 在异步上下文中调用增强方法
            try:
                # 尝试获取当前event loop，如果没有则创建新的
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                enhanced_user_prompt = loop.run_until_complete(enhancer.enhance_prompt(user_prompt))
                
                # 打印增强后的提示词
                print(f"\n{'='*60}")
                print("提示词增强完成")
                print(f"原始提示词: {user_prompt}")
                print(f"增强后提示词: {enhanced_user_prompt}")
                print(f"{'='*60}\n")
                
                # 合并系统提示词和增强后的用户提示词
                if enhanced_user_prompt and enhanced_user_prompt.strip():
                    prompt_text = f"{system_prompt}。{enhanced_user_prompt}"
                else:
                    prompt_text = f"{system_prompt}。{user_prompt}"
            except Exception as e:
                print(f"[提示词增强] 增强失败: {str(e)}，使用原始提示词")
                if user_prompt:
                    prompt_text = f"{system_prompt}。{user_prompt}"
                else:
                    prompt_text = system_prompt
        else:
            # 不使用增强，直接合并系统提示词和用户提示词
            if user_prompt:
                prompt_text = f"{system_prompt}。{user_prompt}"
            else:
                prompt_text = system_prompt
        
        if 'images' not in request.files:
            return jsonify({"error": "缺少图片文件"}), 400
        
        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return jsonify({"error": "没有上传图片文件"}), 400
        
        # 将图片编码为base64
        image_urls = []
        for file in files:
            if file.filename:
                # 读取文件内容
                file_content = file.read()
                encoded_string = base64.b64encode(file_content).decode('utf-8')
                
                # 获取图片格式
                ext = Path(file.filename).suffix.lower()
                if ext == '.jpg':
                    ext = '.jpeg'
                mime_type = f"image/{ext[1:]}" if ext else "image/jpeg"
                image_url = f"data:{mime_type};base64,{encoded_string}"
                image_urls.append(image_url)
        
        if not image_urls:
            return jsonify({"error": "没有有效的图片文件"}), 400
        
        # 同时调用两个API（使用asyncio运行异步函数）
        try:
            # 尝试获取当前event loop，如果没有则创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(call_both_apis(image_urls, prompt_text))
        finally:
            # 不关闭loop，因为可能被其他地方使用
            pass
        
        # 处理结果
        wanx_result = results['wanx']
        doubao_result = results['doubao']
        
        # 检查是否至少有一个模型成功
        if not wanx_result['images'] and not doubao_result['images']:
            error_msg = "两个模型都生成失败"
            if wanx_result['error']:
                error_msg += f"\n通义万相: {wanx_result['error']}"
            if doubao_result['error']:
                error_msg += f"\n豆包API: {doubao_result['error']}"
            return jsonify({
                "success": False,
                "error": error_msg,
                "images": {
                    "wanx": [],
                    "doubao": []
                }
            }), 200
        
        # 保存图片到 Save_picture 目录
        saved_files_wanx = []
        saved_files_doubao = []
        
        for image_data in wanx_result['images']:
            saved_path = save_image_from_base64(image_data, f"{function_id}_wanx")
            if saved_path:
                saved_files_wanx.append(saved_path)
        
        for image_data in doubao_result['images']:
            saved_path = save_image_from_base64(image_data, f"{function_id}_doubao")
            if saved_path:
                saved_files_doubao.append(saved_path)
        
        # 构建返回结果，包含两个模型的图片
        response_data = {
            "success": True,
            "images": {
                "wanx": {
                    "images": wanx_result['images'],
                    "count": len(wanx_result['images']),
                    "error": wanx_result['error'],
                    "saved_files": saved_files_wanx
                },
                "doubao": {
                    "images": doubao_result['images'],
                    "count": len(doubao_result['images']),
                    "error": doubao_result['error'],
                    "saved_files": saved_files_doubao
                }
            },
            "function": function_config.get('name', function_id)
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": f"处理过程中出错: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    print("启动Flask服务器...")
    print("访问 http://localhost:5000 查看前端界面")
    app.run(debug=True, host='0.0.0.0', port=5000)


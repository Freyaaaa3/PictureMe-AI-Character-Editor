#!/usr/bin/env python3
"""
豆包API调用模块
使用豆包API进行图像生成
"""

import os
import base64
import asyncio
import httpx
import concurrent.futures
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 尝试导入豆包SDK
try:
    from volcenginesdkarkruntime import Ark
    from volcenginesdkarkruntime.types.images.images import SequentialImageGenerationOptions
    HAS_DOUBAO_SDK = True
except ImportError:
    HAS_DOUBAO_SDK = False
    print("[豆包API] 警告: volcenginesdkarkruntime 未安装，请运行: pip install volcenginesdkarkruntime")

# 初始化豆包 API Key
api_key = os.getenv("ARK_API_KEY")
if not api_key:
    raise ValueError("ARK_API_KEY 环境变量未设置，请检查.env文件")

# 初始化Ark客户端
client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=api_key,
)

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5


async def download_image_to_base64(image_url):
    """下载图片并转换为base64 data URL"""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http_client:
                response = await http_client.get(image_url)
                if response.status_code == 200 and len(response.content) > 100:
                    content_type = response.headers.get('content-type', 'image/png')
                    mime_type = content_type if 'image/' in content_type else 'image/png'
                    img_base64 = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{mime_type};base64,{img_base64}"
        except Exception:
            if attempt < 2:
                await asyncio.sleep(2)
    return None


async def upload_base64_to_imgbb(base64_data):
    """将base64图片上传到imgbb（免费图片托管服务）"""
    try:
        import httpx
        # 从环境变量获取imgbb API key（可选）
        api_key_imgbb = os.getenv("IMGBB_API_KEY")
        if not api_key_imgbb:
            # 如果没有配置API key，返回None，将使用纯文本生成模式
            return None
        
        upload_url = "https://api.imgbb.com/1/upload"
        
        # 提取base64字符串
        if base64_data.startswith('data:image'):
            _, encoded = base64_data.split(',', 1)
        else:
            encoded = base64_data
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                upload_url,
                data={"key": api_key_imgbb, "image": encoded}
            )
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['url']
    except Exception as e:
        print(f"[豆包API] 上传图片到imgbb失败: {str(e)}")
    return None


async def call_doubao_api(image_urls, prompt_text):
    """
    调用豆包API生成图片
    
    Args:
        image_urls: 输入图片列表（base64 data URL格式或HTTP URL）
        prompt_text: 提示词文本
    
    Returns:
        tuple: (图片列表, 错误信息) 如果成功返回(图片列表, None)，失败返回(None, 错误信息)
    """
    if not HAS_DOUBAO_SDK:
        return None, "volcenginesdkarkruntime 未安装，请运行: pip install volcenginesdkarkruntime"
    
    # 豆包API的images.generate只支持HTTP URL，不支持base64
    # 处理图片输入：如果是base64，尝试上传到图片托管服务；如果是localhost URL，提示错误
    image_list = []
    for img_data in (image_urls or []):
        if not img_data:
            continue
        if img_data.startswith('http://') or img_data.startswith('https://'):
            # HTTP URL
            if 'localhost' in img_data or '127.0.0.1' in img_data:
                return None, "豆包API无法访问本地URL（localhost）。请将Flask服务部署到公网可访问的服务器，或使用图片托管服务。"
            image_list.append(img_data)
        else:
            # base64格式，尝试上传到图片托管服务
            uploaded_url = await upload_base64_to_imgbb(img_data)
            if uploaded_url:
                image_list.append(uploaded_url)
            else:
                # 如果上传失败，提示用户或使用纯文本生成模式
                print(f"[豆包API] 警告: base64图片无法转换为URL（需要配置IMGBB_API_KEY环境变量）")
                print(f"[豆包API] 提示: 将使用纯文本生成模式（不包含输入图片）")
                # 清空image_list，使用纯文本生成
                image_list = []
                break
    
    # 构建API参数--------------------------------------------------------------------------------
    api_params = {
        "model": "doubao-seedream-4-0-250828",
        "prompt": prompt_text,
        "size": "2K",
        "response_format": "url",
        "watermark": True
    }
    
    if image_list:
        api_params["image"] = image_list
        if len(image_list) > 1:
            api_params["sequential_image_generation"] = "auto"
            api_params["sequential_image_generation_options"] = SequentialImageGenerationOptions(
                max_images=min(len(image_list), 3)
            )
    #---------------------------------------------------------------------------------------------
    
    # 重试循环
    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            if attempt > 0:
                await asyncio.sleep(RETRY_DELAY * attempt)
            
            # 在线程池中运行同步API调用
            def sync_api_call():
                try:
                    return client.images.generate(**api_params), None
                except Exception as e:
                    return None, str(e)
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                images_response, api_error = await loop.run_in_executor(executor, sync_api_call)
            
            if api_error:
                error_str = str(api_error)
                # 简化错误消息
                if "InvalidParameter" in error_str:
                    error_msg = f"API参数错误: {api_error}"
                else:
                    error_msg = f"API调用失败: {api_error}"
                
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                return None, error_msg
            
            if not images_response or not hasattr(images_response, 'data'):
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                return None, "API响应格式不正确"
            
            # 提取并下载图片
            images_base64 = []
            for image in images_response.data:
                if hasattr(image, 'url') and image.url:
                    base64_data = await download_image_to_base64(image.url)
                    if base64_data:
                        images_base64.append(base64_data)
            
            if images_base64:
                return images_base64, None
            elif attempt < MAX_RETRY_ATTEMPTS:
                continue
            else:
                return None, "未获取到有效图片"
                
        except Exception as e:
            if attempt < MAX_RETRY_ATTEMPTS:
                continue
            return None, f"调用API时出错: {str(e)}"
    
    return None, "所有重试均失败"

#!/usr/bin/env python3
"""
TT API调用模块
使用TT API进行图像编辑（Midjourney图像编辑）
"""

import os
import base64
import asyncio
import httpx
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化TT API Key
# 使用默认值或从环境变量读取
api_key = os.getenv("TT_API_KEY", "9b9ece59-df55-c566-1157-1f45b7abfca9")
if not api_key:
    raise ValueError("TT_API_KEY 环境变量未设置，请检查.env文件")

# 初始化Hook URL（可选，用于接收回调通知）
hook_url = os.getenv("TT_HOOK_URL", None)

# 配置 HTTP 客户端
http_client = httpx.AsyncClient(
    verify=True,
    timeout=httpx.Timeout(120.0, connect=30.0)
)

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5
RETRY_DELAY_MULTIPLIER = 1.5

# TT API配置
TT_API_SUBMIT_ENDPOINT = "https://api.ttapi.io/midjourney/image-edits/submit"
TT_API_FETCH_ENDPOINT = "https://api.ttapi.io/midjourney/image-edits/fetch"

# 轮询配置
MAX_POLL_ATTEMPTS = 60  # 最多轮询60次
POLL_INTERVAL = 3  # 每次轮询间隔3秒


def extract_base64_from_data_url(data_url):
    """
    从data URL中提取纯base64字符串和MIME类型
    
    Args:
        data_url: data URL格式的字符串，如 "data:image/jpeg;base64,/9j/4AAQ..."
    
    Returns:
        tuple: (mime_type, base64_string) 如 ("image/jpeg", "/9j/4AAQ...")
    """
    if data_url.startswith('data:'):
        # 解析data URL: data:image/jpeg;base64,<base64_data>
        header, encoded = data_url.split(',', 1)
        # 提取MIME类型
        mime_type = header.split(':')[1].split(';')[0]
        return mime_type, encoded
    else:
        # 假设是纯base64字符串，默认MIME类型
        return "image/png", data_url


async def upload_image_to_public_storage(image_data):
    """
    将base64图片上传到公网可访问的存储服务，返回URL
    使用imgbb.com的免费API（无需API key）
    
    Args:
        image_data: base64格式的data URL
    
    Returns:
        str: 图片URL，如果失败返回None
    """
    try:
        # 提取base64数据
        if image_data.startswith('data:image'):
            header, encoded = image_data.split(',', 1)
        else:
            encoded = image_data
        
        # 使用imgbb.com的免费API上传图片
        # 注意：imgbb.com有文件大小限制（32MB）和请求频率限制
        upload_url = "https://api.imgbb.com/1/upload"
        
        # imgbb.com需要API key，但我们可以尝试使用一个公开的key或者提示用户配置
        # 或者使用其他免费服务
        # 这里先返回None，提示需要配置
        print(f"[TT API] 提示: 需要将图片上传到公网可访问的URL")
        print(f"[TT API] 建议: 使用图片上传服务（如imgur、imgbb等）或使用ngrok暴露本地服务")
        return None
        
    except Exception as e:
        print(f"[TT API] 上传图片失败: {str(e)}")
        return None


async def verify_image_url(image_url):
    """
    验证图片URL是否可访问
    
    Args:
        image_url: 图片URL
    
    Returns:
        tuple: (是否可访问, 错误信息, 图片信息)
    """
    try:
        print(f"[TT API] 验证图片URL可访问性: {image_url}")
        
        # 尝试下载图片来验证URL是否可访问
        # ngrok免费版可能需要特殊请求头
        headers = {}
        if 'ngrok' in image_url:
            headers['ngrok-skip-browser-warning'] = 'true'
        
        async with httpx.AsyncClient(
            verify=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            headers=headers
        ) as test_client:
            response = await test_client.get(image_url)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                content_length = len(response.content)
                
                print(f"[TT API] ✓ 图片URL可访问")
                print(f"[TT API]   - Content-Type: {content_type}")
                print(f"[TT API]   - 文件大小: {content_length} bytes")
                
                # 检查是否是图片格式
                if not content_type.startswith('image/'):
                    return False, f"URL返回的不是图片格式，而是: {content_type}", None
                
                # 检查文件大小（至少1KB）
                if content_length < 1024:
                    return False, f"图片文件太小: {content_length} bytes", None
                
                return True, None, {
                    'content_type': content_type,
                    'size': content_length
                }
            else:
                return False, f"HTTP {response.status_code}: {response.text[:200]}", None
                
    except Exception as e:
        return False, f"验证失败: {str(e)}", None


async def submit_image_edit_task(image_url, prompt_text, hook_url=None):
    """
    提交图像编辑任务
    
    Args:
        image_url: 输入图片的URL
        prompt_text: 编辑提示词
        hook_url: 回调URL（可选）
    
    Returns:
        tuple: (job_id, error) 成功返回(job_id, None)，失败返回(None, error)
    """
    headers = {
        "TT-API-KEY": api_key
    }
    
    # 按照TT API规范构建请求数据
    data = {
        "prompt": prompt_text,
        "image": image_url
    }
    
    # 如果提供了hook_url参数，添加到data中
    # 如果没有提供参数，使用模块级别的hook_url配置（从环境变量读取）
    # 注意：这里使用 globals() 来访问模块级别的 hook_url 变量，避免与参数名冲突
    final_hook_url = hook_url if hook_url else globals().get('hook_url')
    if final_hook_url:
        data["hookUrl"] = final_hook_url
        print(f"[TT API] 使用Hook URL: {final_hook_url}")
    
    try:
        print(f"[TT API] 提交图像编辑任务...")
        print(f"[TT API] 图片URL: {image_url}")
        print(f"[TT API] 提示词: {prompt_text[:100]}...")
        
        # 先验证图片URL是否可访问
        is_accessible, verify_error, image_info = await verify_image_url(image_url)
        if not is_accessible:
            error_msg = f"图片URL验证失败: {verify_error}"
            print(f"[TT API] ✗ {error_msg}")
            return None, error_msg
        
        if image_info:
            print(f"[TT API] ✓ 图片信息: {image_info['content_type']}, {image_info['size']} bytes")
        
        # 检查图片URL是否可访问（如果是以localhost开头，TT API可能无法访问）
        if image_url.startswith('http://localhost') or image_url.startswith('https://localhost'):
            print(f"[TT API] 警告: 图片URL是localhost，TT API可能无法访问")
            print(f"[TT API] 提示: TT API需要公网可访问的图片URL")
        
        # 按照TT API规范发送POST请求
        response = await http_client.post(
            TT_API_SUBMIT_ENDPOINT,
            json=data,
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code >= 400:
            try:
                error_result = response.json()
                error_detail = error_result.get('error', error_result.get('message', response.text))
                error_msg = f"HTTP {response.status_code}: {error_detail}"
                
                # 如果是400错误，提供详细的诊断信息
                if response.status_code == 400:
                    print(f"[TT API] ✗ 诊断信息:")
                    print(f"[TT API]   - 图片URL: {image_url}")
                    if 'localhost' in image_url or '127.0.0.1' in image_url:
                        print(f"[TT API]   - URL类型: localhost (TT API无法从外部访问)")
                        print(f"[TT API]   - 解决方案: 需要将图片上传到公网可访问的URL")
                        print(f"[TT API]   - 提示: 可以使用图片上传服务（如imgur）或使用ngrok等工具暴露本地服务")
                    else:
                        print(f"[TT API]   - URL类型: 公网URL")
                    if image_info:
                        print(f"[TT API]   - 图片信息: {image_info['content_type']}, {image_info['size']} bytes")
                    print(f"[TT API]   - 错误详情: {error_detail}")
                    print(f"[TT API]   - 完整响应: {json.dumps(error_result, indent=2, ensure_ascii=False)}")
                    
                    # 如果是"Invalid image or unsupported format"错误，提供更多建议
                    if 'Invalid image' in error_detail or 'unsupported format' in error_detail.lower():
                        print(f"[TT API]   可能的解决方案:")
                        print(f"[TT API]   1. 确保图片格式是PNG或JPG（JPEG）")
                        print(f"[TT API]   2. 确保图片大小在合理范围内（建议100KB-10MB）")
                        print(f"[TT API]   3. 确保图片URL可以直接访问（不需要认证）")
                        print(f"[TT API]   4. 尝试使用不同的图片格式（如PNG）")
                        if 'ngrok' in image_url:
                            print(f"[TT API]   5. ⚠️ 重要: TT API可能无法通过ngrok访问图片")
                            print(f"[TT API]      建议: 使用图片上传服务（如imgur、imgbb）上传图片，然后使用上传后的URL")
                            print(f"[TT API]      或者: 使用付费的ngrok计划，或使用其他内网穿透工具")
                
                return None, error_msg
            except:
                error_text = response.text[:500]
                print(f"[TT API] 错误响应: {error_text}")
                return None, f"HTTP {response.status_code}: {error_text}"
        
        result = response.json()
        
        # 提取jobId
        job_id = None
        if 'data' in result and isinstance(result['data'], dict):
            job_id = result['data'].get('jobId') or result['data'].get('job_id')
        elif 'jobId' in result:
            job_id = result['jobId']
        elif 'job_id' in result:
            job_id = result['job_id']
        
        if job_id:
            print(f"[TT API] 任务提交成功，Job ID: {job_id}")
            return job_id, None
        else:
            error_msg = "响应中未找到jobId"
            print(f"[TT API] {error_msg}")
            print(f"[TT API] 响应内容: {json.dumps(result, indent=2)[:500]}")
            return None, error_msg
            
    except Exception as e:
        return None, f"提交任务失败: {str(e)}"


async def fetch_image_edit_result(job_id):
    """
    获取图像编辑任务结果
    
    Args:
        job_id: 任务ID
    
    Returns:
        tuple: (图片URL列表, 错误信息) 成功返回(图片URL列表, None)，失败返回(None, 错误信息)
    """
    headers = {
        "TT-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "jobId": job_id
    }
    
    try:
        response = await http_client.post(
            TT_API_FETCH_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code >= 400:
            try:
                error_result = response.json()
                error_detail = error_result.get('error', error_result.get('message', response.text))
                return None, f"HTTP {response.status_code}: {error_detail}"
            except:
                return None, f"HTTP {response.status_code}: {response.text[:200]}"
        
        result = response.json()
        
        # 添加调试信息，输出完整响应
        print(f"[TT API] 获取任务结果响应: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
        
        # 检查任务状态
        # TT API的响应格式：顶层有status字段，data中也有相关信息
        top_level_status = result.get('status', '')
        data = result.get('data', {})
        
        # 如果data不是字典，可能是其他格式
        if not isinstance(data, dict):
            print(f"[TT API] 警告: data字段不是字典类型，实际类型: {type(data)}")
            print(f"[TT API] data内容: {data}")
            # 尝试直接从result中获取状态
            task_status = top_level_status or result.get('task_status') or result.get('state')
            if task_status:
                data = result  # 使用整个result作为data
            else:
                return None, f"响应格式不正确: data不是字典且无法找到状态字段"
        
        if isinstance(data, dict):
            # 优先从顶层获取状态（TT API的status在顶层）
            task_status = top_level_status or data.get('status') or data.get('task_status') or data.get('state') or data.get('taskStatus')
            
            print(f"[TT API] 任务状态: {task_status}")
            
            if task_status in ['SUCCESS', 'COMPLETED', 'DONE', 'FINISHED']:
                # 任务完成，提取图片URL
                image_urls = []
                
                # 优先使用cdnImages（TT API的CDN，更可靠），如果没有再使用images
                cdn_images = data.get('cdnImages')
                images = data.get('images')
                
                # 优先处理cdnImages
                if cdn_images:
                    if isinstance(cdn_images, list):
                        for img in cdn_images:
                            if isinstance(img, str):
                                image_urls.append(img)
                            elif isinstance(img, dict):
                                url = img.get('url') or img.get('image_url') or img.get('imageUrl')
                                if url:
                                    image_urls.append(url)
                    elif isinstance(cdn_images, str):
                        image_urls.append(cdn_images)
                
                # 如果cdnImages为空，再尝试images
                if not image_urls and images:
                    if isinstance(images, list):
                        for img in images:
                            if isinstance(img, str):
                                image_urls.append(img)
                            elif isinstance(img, dict):
                                url = img.get('url') or img.get('image_url') or img.get('imageUrl')
                                if url:
                                    image_urls.append(url)
                    elif isinstance(images, str):
                        image_urls.append(images)
                
                # 也尝试其他可能的字段名
                if not image_urls:
                    image_url = data.get('image_url') or data.get('imageUrl') or data.get('image')
                    if image_url:
                        image_urls.append(image_url)
                
                # 也可能返回图片数组
                if not image_urls:
                    image_list = data.get('image_list')
                    if isinstance(image_list, list):
                        for img in image_list:
                            if isinstance(img, str):
                                image_urls.append(img)
                            elif isinstance(img, dict):
                                url = img.get('url') or img.get('image_url')
                                if url:
                                    image_urls.append(url)
                
                if image_urls:
                    # TT API默认生成4张图片，只取第一张
                    print(f"[TT API] ✓ 任务完成，找到 {len(image_urls)} 张图片，只使用第一张")
                    return [image_urls[0]], None
                else:
                    print(f"[TT API] ⚠️ 任务完成但未找到图片URL")
                    print(f"[TT API] data内容: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                    return None, "任务完成但未找到图片URL"
                    
            elif task_status in ['FAILED', 'ERROR']:
                error_msg = data.get('message') or data.get('error') or "任务执行失败"
                return None, f"任务失败: {error_msg}"
                
            elif task_status in ['PENDING', 'PROCESSING', 'RUNNING', 'IN_PROGRESS', 'QUEUED', 'WAITING', 'ON_QUEUE', 'IN_QUEUE']:
                # 任务还在处理中
                progress = data.get('progress', 'N/A')
                print(f"[TT API] 任务处理中，状态: {task_status}, 进度: {progress}%")
                return None, "PENDING"
            elif task_status is None:
                # 状态为None，可能是任务还在处理中，或者响应格式不同
                print(f"[TT API] 警告: 无法从响应中提取任务状态")
                print(f"[TT API] 尝试检查是否任务已完成但没有状态字段...")
                
                # 尝试直接查找图片URL，可能任务已完成但没有明确的状态字段
                image_urls = []
                image_url = data.get('image_url') or data.get('imageUrl') or data.get('image') or result.get('image_url') or result.get('imageUrl')
                if image_url:
                    image_urls.append(image_url)
                    print(f"[TT API] 找到图片URL（无状态字段）: {image_url}")
                    return image_urls, None
                
                # 如果找不到图片URL，可能是任务还在处理中
                print(f"[TT API] 未找到图片URL，假设任务仍在处理中...")
                return None, "PENDING"
            else:
                # 未知状态
                print(f"[TT API] 未知任务状态: {task_status}")
                print(f"[TT API] 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
                return None, f"未知任务状态: {task_status}"
        else:
            print(f"[TT API] 响应格式不正确: data不是字典")
            print(f"[TT API] 完整响应: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
            return None, "响应格式不正确"
            
    except Exception as e:
        return None, f"获取结果失败: {str(e)}"


async def download_image_to_base64(image_url, max_retries=3):
    """
    下载图片并转换为base64 data URL（带重试机制）
    
    Args:
        image_url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        str: base64 data URL格式的图片，失败返回None
    """
    for attempt in range(max_retries):
        try:
            print(f"[TT API] 下载图片 (尝试 {attempt + 1}/{max_retries}): {image_url[:100]}...")
            
            # 设置请求头，某些CDN可能需要User-Agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = await http_client.get(
                image_url, 
                timeout=30.0, 
                follow_redirects=True,
                headers=headers
            )
            
            if response.status_code == 200:
                img_base64 = base64.b64encode(response.content).decode('utf-8')
                content_type = response.headers.get('content-type', 'image/png')
                
                # 验证内容确实是图片
                if len(response.content) < 100:
                    print(f"[TT API] 警告: 下载的内容太小 ({len(response.content)} bytes)，可能不是有效图片")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)  # 等待后重试
                        continue
                    return None
                
                if 'image/' in content_type:
                    mime_type = content_type
                else:
                    # 从URL推断格式
                    if image_url.endswith('.jpg') or image_url.endswith('.jpeg'):
                        mime_type = 'image/jpeg'
                    elif image_url.endswith('.png'):
                        mime_type = 'image/png'
                    elif image_url.endswith('.webp'):
                        mime_type = 'image/webp'
                    else:
                        mime_type = 'image/png'
                
                print(f"[TT API] ✓ 图片下载成功 ({len(response.content)} bytes, {mime_type})")
                return f"data:{mime_type};base64,{img_base64}"
            else:
                error_msg = f"HTTP {response.status_code}"
                print(f"[TT API] ✗ 下载失败: {error_msg}")
                if response.status_code == 403:
                    print(f"[TT API]   403错误: 可能被CDN阻止，尝试添加请求头")
                elif response.status_code == 404:
                    print(f"[TT API]   404错误: 图片URL不存在")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # 等待后重试
                    continue
                return None
                
        except httpx.TimeoutException as e:
            print(f"[TT API] ✗ 下载超时: {str(e)}")
            if attempt < max_retries - 1:
                print(f"[TT API]   等待后重试...")
                await asyncio.sleep(3)
                continue
            return None
        except httpx.RequestError as e:
            print(f"[TT API] ✗ 请求错误: {str(e)}")
            if attempt < max_retries - 1:
                print(f"[TT API]   等待后重试...")
                await asyncio.sleep(2)
                continue
            return None
        except Exception as e:
            print(f"[TT API] ✗ 下载图片失败: {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            return None
    
    print(f"[TT API] ✗ 图片下载失败，已重试 {max_retries} 次")
    return None


async def call_tt_api(image_urls, prompt_text):
    """
    调用TT API进行图像编辑
    
    Args:
        image_urls: 输入图片列表（base64格式的data URL或HTTP URL）
        prompt_text: 编辑提示词
    
    Returns:
        tuple: (图片列表, 错误信息) 如果成功返回(图片列表, None)，失败返回(None, 错误信息)
    """
    # 检查是否有输入图片
    if not image_urls or len(image_urls) == 0:
        return None, "图像编辑需要提供输入图片"
    
    # 获取第一张图片
    input_image = image_urls[0]
    
    # 判断输入图片格式
    image_url = None
    if input_image.startswith('http://') or input_image.startswith('https://'):
        # 已经是URL格式
        image_url = input_image
        print(f"[TT API] 使用HTTP URL: {image_url}")
        
        # 检查是否是localhost URL（TT API无法从外部访问）
        if 'localhost' in image_url or '127.0.0.1' in image_url:
            error_msg = f"TT API无法访问localhost URL: {image_url}"
            print(f"[TT API] ✗ {error_msg}")
            print(f"[TT API] 解决方案:")
            print(f"[TT API]   1. 使用ngrok暴露本地服务:")
            print(f"[TT API]      - 安装ngrok: https://ngrok.com/")
            print(f"[TT API]      - 运行: ngrok http 5000")
            print(f"[TT API]      - 使用ngrok提供的公网URL")
            print(f"[TT API]   2. 将图片上传到公网可访问的图片托管服务")
            print(f"[TT API]   3. 使用公网IP替代localhost")
            return None, error_msg
    elif input_image.startswith('data:image'):
        # 是base64 data URL，需要转换为HTTP URL
        error_msg = "TT API图像编辑需要公网可访问的图片URL，当前输入是base64格式"
        print(f"[TT API] ✗ {error_msg}")
        print(f"[TT API] 解决方案:")
        print(f"[TT API]   1. 使用ngrok暴露本地Flask服务，然后使用ngrok URL")
        print(f"[TT API]   2. 将图片上传到公网图片托管服务（如imgur）")
        return None, error_msg
    else:
        return None, "不支持的图片格式"
    
    # 重试循环
    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            if attempt > 0:
                delay = RETRY_DELAY * (RETRY_DELAY_MULTIPLIER ** (attempt - 1))
                await asyncio.sleep(delay)
            
            print(f"[TT API] 开始调用API (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS + 1})...")
            
            # 步骤1: 提交任务（使用模块级别的hook_url配置，如果设置了的话）
            # 使用 globals() 访问模块级别的 hook_url 变量
            module_hook_url = globals().get('hook_url')
            job_id, error = await submit_image_edit_task(image_url, prompt_text, hook_url=module_hook_url)
            if error:
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error
            
            # 步骤2: 轮询任务结果
            print(f"[TT API] 开始轮询任务结果...")
            for poll_attempt in range(MAX_POLL_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL)
                
                image_urls_result, fetch_error = await fetch_image_edit_result(job_id)
                
                if fetch_error == "PENDING":
                    # 任务还在处理中，继续轮询
                    if (poll_attempt + 1) % 10 == 0:
                        print(f"[TT API] 任务处理中... (已等待 {(poll_attempt + 1) * POLL_INTERVAL}秒)")
                    continue
                elif fetch_error:
                    # 任务失败
                    return None, fetch_error
                elif image_urls_result:
                    # 任务成功，下载图片并转换为base64
                    # 注意：image_urls_result 现在只包含第一张图片（已在fetch_image_edit_result中处理）
                    print(f"[TT API] 任务完成，获取到 {len(image_urls_result)} 张图片URL")
                    images_base64 = []
                    
                    for idx, img_url in enumerate(image_urls_result):
                        print(f"[TT API] 开始下载第 {idx + 1} 张图片...")
                        base64_data = await download_image_to_base64(img_url)
                        if base64_data:
                            images_base64.append(base64_data)
                            print(f"[TT API] ✓ 第 {idx + 1} 张图片下载成功")
                        else:
                            print(f"[TT API] ✗ 第 {idx + 1} 张图片下载失败")
                    
                    if images_base64:
                        print(f"[TT API] 成功生成 {len(images_base64)} 张图片")
                        return images_base64, None
                    else:
                        error_details = []
                        for idx, img_url in enumerate(image_urls_result):
                            error_details.append(f"图片 {idx + 1}: {img_url[:80]}...")
                        return None, f"所有图片下载失败。URL列表:\n" + "\n".join(error_details)
            
            # 轮询超时
            return None, f"任务处理超时（已等待 {MAX_POLL_ATTEMPTS * POLL_INTERVAL}秒）"
            
        except Exception as e:
            error_msg = f"调用API时出错: {type(e).__name__}: {str(e)}"
            print(f"[TT API] {error_msg}")
            import traceback
            print(f"[TT API] 错误详情: {traceback.format_exc()}")
            if attempt < MAX_RETRY_ATTEMPTS:
                continue
            else:
                return None, error_msg
    
    return None, "所有重试均失败"

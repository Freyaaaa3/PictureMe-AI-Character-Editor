#!/usr/bin/env python3
"""
通义万相API调用模块
提供图片生成功能
"""

import os
import base64
import asyncio
import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化通义万相 API Key
api_key = os.getenv("QWEN_API_KEY")
if not api_key:
    raise ValueError("QWEN_API_KEY 环境变量未设置，请检查.env文件")

# 禁用系统代理环境变量，避免代理连接错误
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# 配置 HTTP 客户端
http_client = httpx.AsyncClient(
    verify=False,  # 禁用SSL验证以避免SSL错误（仅用于开发环境）
    timeout=httpx.Timeout(60.0, connect=10.0)  # 设置超时时间
)

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5
RETRY_DELAY_MULTIPLIER = 1.5


async def create_image_task(image_urls, prompt_text):
    """创建图片生成任务，返回任务ID"""
    # 设置请求头（符合API规范）
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'X-DashScope-Async': 'enable'
    }
    
    # 根据是否有输入图片选择不同的端点和模型
    if image_urls:
        # 图片生成图片
        url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis'
        # 处理图片数据：确保格式为 data:image/xxx;base64,xxx
        processed_images = []
        for img_data in image_urls:
            if img_data.startswith('data:image'):
                # 已经是正确的格式
                processed_images.append(img_data)
            else:
                # 如果不是data URL格式，假设是base64字符串，添加前缀
                processed_images.append(f"data:image/png;base64,{img_data}")
        
        payload = {
            'model': 'wan2.5-i2i-preview',
            'input': {
                'prompt': prompt_text,
                'images': processed_images  # 使用 images 数组，不是 image
            },
            'parameters': {
                'n': 1
            }
        }
    else:
        # 文本生成图片
        url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'
        payload = {
            'model': 'wanx-v1',
            'input': {
                'prompt': prompt_text
            },
            'parameters': {
                'size': '1024*1024',
                'n': 1
            }
        }
    
    try:
        response = await http_client.post(url, json=payload, headers=headers, timeout=30.0)
        
        # 检查状态码
        if response.status_code >= 400:
            try:
                error_result = response.json()
                error_detail = error_result.get('message', error_result.get('error', response.text))
                return None, f"HTTP {response.status_code}: {error_detail}"
            except:
                return None, f"HTTP {response.status_code}: {response.text[:200]}"
        
        # 解析响应
        try:
            result = response.json()
        except Exception as json_err:
            return None, f"响应解析失败: {str(json_err)}"
        
        # 检查响应结构并提取 task_id
        output = result.get('output', {})
        if 'task_id' in output:
            return output['task_id'], None
        else:
            error_detail = output.get('message', result.get('message', '未知错误'))
            return None, f"创建任务失败: {error_detail}"
            
    except httpx.HTTPStatusError as e:
        try:
            error_response = e.response.json()
            error_detail = error_response.get('message', error_response.get('error', e.response.text))
        except:
            error_detail = e.response.text
        return None, f"HTTP错误 {e.response.status_code}: {error_detail}"
        
    except httpx.TimeoutException as e:
        return None, f"请求超时: {str(e)}"
        
    except Exception as e:
        return None, f"创建任务时出错: {type(e).__name__}: {str(e)}"


async def query_task_status(task_id):
    """查询任务状态"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
    
    try:
        response = await http_client.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP错误: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        return None, f"查询任务状态时出错: {str(e)}"


async def call_wanx_api(image_urls, prompt_text):
    """调用通义万相API生成图片，带重试机制（使用标准HTTP API）"""
    # 重试循环
    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            if attempt > 0:
                # 计算重试延迟（指数退避）
                delay = RETRY_DELAY * (RETRY_DELAY_MULTIPLIER ** (attempt - 1))
                await asyncio.sleep(delay)
            
            # 步骤1: 创建任务
            task_id, error = await create_image_task(image_urls, prompt_text)
            if error:
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error
            
            # 步骤2: 轮询任务状态直到完成
            # 轮询配置：最多等待5分钟（300秒），使用动态间隔
            max_wait_time = 300  # 最大等待时间（秒）
            initial_interval = 2  # 初始间隔2秒（任务刚开始时频繁查询）
            max_interval = 5  # 最大间隔5秒（任务运行一段时间后降低查询频率）
            current_interval = initial_interval
            elapsed_time = 0
            poll_count = 0
            task_completed = False
            
            while elapsed_time < max_wait_time:
                await asyncio.sleep(current_interval)
                elapsed_time += current_interval
                poll_count += 1
                
                task_result, query_error = await query_task_status(task_id)
                if query_error:
                    # 查询错误时，增加等待时间后重试
                    if elapsed_time < max_wait_time - 10:
                        current_interval = min(current_interval + 1, max_interval)
                        continue
                    else:
                        return None, f"查询任务状态失败: {query_error}"
                
                # 检查任务状态
                task_status = task_result.get('output', {}).get('task_status', '')
                if poll_count % 10 == 0:  # 每10次打印一次状态
                    remaining_time = max_wait_time - elapsed_time
                    print(f"[通义万相] 任务状态 (轮询 {poll_count}次, 已等待 {elapsed_time}秒, 剩余 {remaining_time}秒): {task_status}")
                
                if task_status == 'SUCCEEDED':
                    task_completed = True
                    # 提取图片URL
                    image_urls_result = []
                    results = task_result.get('output', {}).get('results', [])
                    for result in results:
                        if isinstance(result, dict) and 'url' in result:
                            image_urls_result.append(result['url'])
                        elif hasattr(result, 'url'):
                            image_urls_result.append(result.url)
                    
                    if image_urls_result:
                        # 将图片URL转换为base64格式
                        images_base64 = []
                        for img_url in image_urls_result:
                            # 下载图片的重试机制
                            download_success = False
                            for download_attempt in range(3):  # 最多重试3次
                                try:
                                    img_response = await http_client.get(
                                        img_url,
                                        timeout=30.0,
                                        follow_redirects=True
                                    )
                                    if img_response.status_code == 200:
                                        img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                                        images_base64.append(f"data:image/png;base64,{img_base64}")
                                        download_success = True
                                        break
                                except Exception as e:
                                    if download_attempt < 2:
                                        await asyncio.sleep(2)
                                        continue
                            
                            # 如果所有重试都失败，直接使用URL
                            if not download_success:
                                images_base64.append(img_url)
                        
                        # 直接返回图片列表
                        return images_base64, None
                    else:
                        return None, "任务成功但未返回图片"
                
                elif task_status == 'FAILED':
                    error_message = task_result.get('output', {}).get('message', '任务执行失败')
                    return None, f"任务执行失败: {error_message}"
                
                elif task_status in ['PENDING', 'RUNNING']:
                    # 任务还在运行，使用动态间隔：运行时间越长，查询间隔越大
                    # 前30秒：每2秒查询一次，之后逐渐增加到5秒
                    if elapsed_time < 30:
                        current_interval = initial_interval
                    else:
                        current_interval = min(current_interval + 0.5, max_interval)
                    continue
                else:
                    # 未知状态，继续轮询
                    current_interval = min(current_interval + 1, max_interval)
                    continue
            
            # 如果轮询超时
            if not task_completed:
                error_msg = f"等待任务完成超时（已等待 {elapsed_time}秒）"
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error_msg
            
        except Exception as e:
            if attempt < MAX_RETRY_ATTEMPTS:
                continue
            else:
                return None, str(e)
    
    return None, "所有重试均失败"


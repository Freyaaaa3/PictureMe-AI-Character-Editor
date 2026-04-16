#!/usr/bin/env python3
"""
Gemini API调用模块
使用Google Gemini原生API进行图片生成
"""

import os
import base64
import asyncio
import httpx
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化Gemini API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY 环境变量未设置，请检查.env文件")

# 配置代理（如果需要访问Google服务，可能需要代理）
proxy_url = os.getenv("GEMINI_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")

# 配置 HTTP 客户端
# 使用环境变量方式（httpx会自动读取HTTPS_PROXY和HTTP_PROXY）
if proxy_url:
    # 设置环境变量，httpx会自动读取
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['HTTP_PROXY'] = proxy_url
    print(f"[Gemini] 已配置代理: {proxy_url}")
    print(f"[Gemini] 环境变量 HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")
else:
    print(f"[Gemini] 未配置代理，将直接连接")
    print(f"[Gemini] 提示: 如果无法连接，请在.env文件中设置 GEMINI_PROXY=http://127.0.0.1:7890")

# 保存代理URL供后续使用
GEMINI_PROXY_URL = proxy_url

# 注意：不在模块级别创建客户端，而是在函数内部创建
# 这样可以确保环境变量已正确设置

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5
RETRY_DELAY_MULTIPLIER = 1.5

# Gemini API配置
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com"
GEMINI_MODEL = "gemini-2.0-flash-exp-image-generation"


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


async def call_gemini_api(image_urls, prompt_text):
    """
    调用Gemini API生成图片（使用Google Gemini原生API）
    
    Args:
        image_urls: 输入图片列表（base64格式的data URL）
        prompt_text: 提示词文本
    
    Returns:
        tuple: (图片列表, 错误信息) 如果成功返回(图片列表, None)，失败返回(None, 错误信息)
    """
    # 在函数内部创建客户端，确保环境变量已设置
    # 如果配置了代理，确保环境变量已设置（httpx会自动从环境变量读取）
    current_proxy = os.getenv("GEMINI_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if current_proxy:
        # 设置环境变量，httpx会自动读取
        os.environ['HTTPS_PROXY'] = current_proxy
        os.environ['HTTP_PROXY'] = current_proxy
        print(f"[Gemini] 已设置代理环境变量: {current_proxy}")
        print(f"[Gemini] HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")
        print(f"[Gemini] HTTP_PROXY={os.environ.get('HTTP_PROXY')}")
    
    # 创建HTTP客户端
    # httpx会自动从环境变量 HTTPS_PROXY 和 HTTP_PROXY 读取代理配置
    # 注意：某些版本的httpx可能不支持proxies参数，所以使用环境变量方式
    async with httpx.AsyncClient(
        verify=True,
        timeout=httpx.Timeout(120.0, connect=30.0)
    ) as http_client:
        # 重试循环
        for attempt in range(MAX_RETRY_ATTEMPTS + 1):
            try:
                if attempt > 0:
                    # 计算重试延迟（指数退避）
                    delay = RETRY_DELAY * (RETRY_DELAY_MULTIPLIER ** (attempt - 1))
                    await asyncio.sleep(delay)
                
                # 构建parts数组
                parts = []
                
                # 添加文本提示
                parts.append({
                    "text": prompt_text
                })
                
                # 添加图片（如果有）
                if image_urls:
                    for img_data in image_urls:
                        # 提取base64和MIME类型
                        mime_type, base64_data = extract_base64_from_data_url(img_data)
                        
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64_data
                            }
                        })
                
                # 构建请求payload
                payload = {
                    "contents": [
                        {
                            "parts": parts
                        }
                    ],
                    "generationConfig": {
                        "responseModalities": [
                            "TEXT",
                            "IMAGE"
                        ]
                    }
                }
                
                # 构建请求URL
                url = f"{GEMINI_API_BASE_URL}/v1beta/models/{GEMINI_MODEL}:generateContent"
                
                # 构建请求头
                headers = {
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                }
                
                print(f"[Gemini] 开始调用API (尝试 {attempt + 1}/{MAX_RETRY_ATTEMPTS + 1})...")
                print(f"[Gemini] 端点: {url}")
                print(f"[Gemini] 提示词: {prompt_text[:100]}...")
                if current_proxy:
                    print(f"[Gemini] 使用代理连接: {current_proxy}")
                else:
                    print(f"[Gemini] 直接连接（未使用代理）")
                
                # 发送请求
                # 注意: httpx会自动从环境变量读取代理，无需在请求时传递
                try:
                    response = await http_client.post(url, json=payload, headers=headers, timeout=120.0)
                except httpx.ConnectError as e:
                    error_msg = f"连接失败: {str(e)}"
                    print(f"[Gemini] {error_msg}")
                    
                    # 提供详细的诊断信息
                    if current_proxy:
                        print(f"[Gemini] 诊断信息:")
                        print(f"[Gemini]   - 配置的代理: {current_proxy}")
                        print(f"[Gemini]   - 环境变量 HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', '未设置')}")
                        print(f"[Gemini]   - 环境变量 HTTP_PROXY: {os.environ.get('HTTP_PROXY', '未设置')}")
                        print(f"[Gemini] 可能的原因:")
                        print(f"[Gemini]   1. 代理服务未运行（请检查代理软件是否启动）")
                        print(f"[Gemini]   2. 代理地址/端口不正确")
                        print(f"[Gemini]   3. 代理需要认证（当前不支持认证代理）")
                        print(f"[Gemini]   4. 防火墙阻止连接")
                    else:
                        print(f"[Gemini] 提示: 如果在中国大陆，可能需要配置代理。")
                        print(f"[Gemini] 请在.env文件中设置 GEMINI_PROXY 环境变量，例如: GEMINI_PROXY=http://127.0.0.1:7890")
                    
                    if attempt < MAX_RETRY_ATTEMPTS:
                        continue
                    else:
                        return None, error_msg
                
                # 检查状态码
                if response.status_code >= 400:
                    try:
                        error_result = response.json()
                        error_detail = error_result.get('error', {}).get('message', error_result.get('message', response.text))
                        error_msg = f"HTTP {response.status_code}: {error_detail}"
                        print(f"[Gemini] API调用失败: {error_msg}")
                        if attempt < MAX_RETRY_ATTEMPTS:
                            continue
                        else:
                            return None, error_msg
                    except:
                        error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                        print(f"[Gemini] API调用失败: {error_msg}")
                        if attempt < MAX_RETRY_ATTEMPTS:
                            continue
                        else:
                            return None, error_msg
                
                # 解析响应
                try:
                    result = response.json()
                except Exception as json_err:
                    error_msg = f"响应解析失败: {str(json_err)}"
                    print(f"[Gemini] {error_msg}")
                    print(f"[Gemini] 响应内容: {response.text[:500]}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        continue
                    else:
                        return None, error_msg
                
                # 提取图片
                images_base64 = []
                
                # Gemini API响应结构：
                # {
                #   "candidates": [
                #     {
                #       "content": {
                #         "parts": [
                #           {
                #             "text": "...",
                #             "inline_data": {
                #               "mime_type": "image/png",
                #               "data": "base64_string"
                #             }
                #           }
                #         ]
                #       }
                #     }
                #   ]
                # }
                
                candidates = result.get('candidates', [])
                if not candidates:
                    error_msg = "响应中没有candidates字段"
                    print(f"[Gemini] {error_msg}")
                    print(f"[Gemini] 响应内容: {json.dumps(result, indent=2)[:1000]}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        continue
                    else:
                        return None, error_msg
                
                # 从candidates中提取图片
                for candidate in candidates:
                    content = candidate.get('content', {})
                    parts = content.get('parts', [])
                    
                    for part in parts:
                        # 检查是否有inline_data（图片）
                        if 'inline_data' in part:
                            inline_data = part.get('inline_data', {})
                            mime_type = inline_data.get('mime_type', 'image/png')
                            base64_data = inline_data.get('data', '')
                            
                            if base64_data:
                                # 转换为data URL格式
                                data_url = f"data:{mime_type};base64,{base64_data}"
                                images_base64.append(data_url)
                
                if images_base64:
                    print(f"[Gemini] 成功生成 {len(images_base64)} 张图片")
                    return images_base64, None
                else:
                    error_msg = "响应中未找到图片数据"
                    print(f"[Gemini] {error_msg}")
                    print(f"[Gemini] 响应内容: {json.dumps(result, indent=2)[:1000]}")
                    if attempt < MAX_RETRY_ATTEMPTS:
                        continue
                    else:
                        return None, error_msg
                        
            except httpx.HTTPStatusError as e:
                try:
                    error_response = e.response.json()
                    error_detail = error_response.get('error', {}).get('message', error_response.get('message', e.response.text))
                except:
                    error_detail = e.response.text
                error_msg = f"HTTP错误 {e.response.status_code}: {error_detail}"
                print(f"[Gemini] {error_msg}")
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error_msg
                    
            except httpx.TimeoutException as e:
                error_msg = f"请求超时: {str(e)}"
                print(f"[Gemini] {error_msg}")
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error_msg
                    
            except Exception as e:
                error_msg = f"调用API时出错: {type(e).__name__}: {str(e)}"
                print(f"[Gemini] {error_msg}")
                import traceback
                print(f"[Gemini] 错误详情: {traceback.format_exc()}")
                if attempt < MAX_RETRY_ATTEMPTS:
                    continue
                else:
                    return None, error_msg
        
        return None, "所有重试均失败"

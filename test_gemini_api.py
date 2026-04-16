#!/usr/bin/env python3
"""
Gemini API 测试脚本
用于测试Gemini API调用是否成功，以及能否正确捕获生成的图片
"""

import os
import asyncio
import base64
from pathlib import Path
from dotenv import load_dotenv
from gemini_api import call_gemini_api, extract_base64_from_data_url

# 加载环境变量
load_dotenv()

# 测试用的输出目录
TEST_OUTPUT_DIR = Path("test_output")
TEST_OUTPUT_DIR.mkdir(exist_ok=True)


def save_test_image(image_data, filename):
    """保存测试图片"""
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
        
        # 保存文件
        filepath = TEST_OUTPUT_DIR / f"{filename}.{image_format}"
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        print(f"  ✓ 图片已保存: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"  ✗ 保存图片失败: {str(e)}")
        return None


async def test_text_to_image():
    """测试文本生成图片"""
    print("\n" + "="*60)
    print("测试 1: 文本生成图片")
    print("="*60)
    
    prompt = "Generate a beautiful sunset landscape with mountains and a lake"
    print(f"提示词: {prompt}")
    
    try:
        images, error = await call_gemini_api([], prompt)
        
        if error:
            print(f"✗ 调用失败: {error}")
            return False
        
        if images and len(images) > 0:
            print(f"✓ 成功生成 {len(images)} 张图片")
            for i, img_data in enumerate(images):
                save_test_image(img_data, f"test_text_to_image_{i+1}")
            return True
        else:
            print("✗ 未生成图片")
            return False
            
    except Exception as e:
        print(f"✗ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_image_to_image():
    """测试图片生成图片（需要提供测试图片）"""
    print("\n" + "="*60)
    print("测试 2: 图片生成图片")
    print("="*60)
    
    # 检查是否有测试图片
    test_image_path = Path("test_input.jpg")  # 可以改为你的测试图片路径
    
    if not test_image_path.exists():
        print(f"⚠ 未找到测试图片: {test_image_path}")
        print("  跳过图片生成图片测试")
        print("  提示: 可以创建一个 test_input.jpg 文件来测试此功能")
        return None
    
    try:
        # 读取测试图片并转换为base64
        with open(test_image_path, 'rb') as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_data_url = f"data:image/jpeg;base64,{image_base64}"
        
        prompt = "Apply a vintage photo filter to this image"
        print(f"提示词: {prompt}")
        print(f"输入图片: {test_image_path}")
        
        images, error = await call_gemini_api([image_data_url], prompt)
        
        if error:
            print(f"✗ 调用失败: {error}")
            return False
        
        if images and len(images) > 0:
            print(f"✓ 成功生成 {len(images)} 张图片")
            for i, img_data in enumerate(images):
                save_test_image(img_data, f"test_image_to_image_{i+1}")
            return True
        else:
            print("✗ 未生成图片")
            return False
            
    except Exception as e:
        print(f"✗ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_proxy_connection():
    """测试代理连接"""
    print("\n" + "="*60)
    print("测试 0.5: 代理连接测试")
    print("="*60)
    
    proxy_url = os.getenv("GEMINI_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    
    if not proxy_url:
        print("⚠ 未配置代理，跳过代理测试")
        return None
    
    print(f"测试代理: {proxy_url}")
    
    # 检查代理服务是否在运行（简单检查端口是否开放）
    try:
        from urllib.parse import urlparse
        parsed = urlparse(proxy_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 7890
        
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✓ 代理端口 {host}:{port} 可访问")
        else:
            print(f"✗ 代理端口 {host}:{port} 无法连接")
            print("  请检查代理服务是否正在运行")
            return False
    except Exception as e:
        print(f"⚠ 端口检查失败: {str(e)}")
        print("  继续测试代理连接...")
    
    try:
        import httpx
        # 使用环境变量方式配置代理（httpx会自动读取）
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['HTTP_PROXY'] = proxy_url
        print(f"  已设置环境变量: HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")
        
        # 创建客户端（httpx会自动从环境变量读取代理）
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 尝试通过代理访问一个简单的网站
            test_url = "https://www.google.com"
            try:
                response = await client.get(test_url, timeout=5.0)
                print(f"✓ 代理连接成功 (状态码: {response.status_code})")
                return True
            except httpx.ConnectError as e:
                print(f"✗ 代理连接失败: {str(e)}")
                print("  可能原因:")
                print("    1. 代理服务未运行")
                print("    2. 代理地址/端口不正确")
                print("    3. 代理需要认证")
                print("    4. 防火墙阻止连接")
                return False
            except Exception as e:
                print(f"⚠ 代理测试异常: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
    except Exception as e:
        print(f"✗ 代理测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_connection():
    """测试API连接和基本功能"""
    print("\n" + "="*60)
    print("测试 0: API连接测试")
    print("="*60)
    
    # 检查API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("✗ GEMINI_API_KEY 未设置")
        print("  请在 .env 文件中设置 GEMINI_API_KEY")
        return False
    
    print(f"✓ API Key 已配置 (长度: {len(api_key)} 字符)")
    
    # 检查代理配置
    proxy_url = os.getenv("GEMINI_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy_url:
        print(f"✓ 代理已配置: {proxy_url}")
        print(f"  环境变量 HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', '未设置')}")
    else:
        print("⚠ 未配置代理（如果在中国大陆可能需要代理）")
    
    # 测试简单调用
    print("\n测试简单API调用...")
    simple_prompt = "Generate a simple red circle on white background"
    try:
        images, error = await call_gemini_api([], simple_prompt)
        
        if error:
            print(f"✗ API调用失败: {error}")
            if "connection" in error.lower() or "connect" in error.lower():
                print("\n提示: 连接失败可能是以下原因：")
                print("  1. 网络连接问题")
                print("  2. 需要配置代理（在中国大陆）")
                print("  3. 防火墙阻止连接")
            return False
        
        if images and len(images) > 0:
            print(f"✓ API调用成功，生成了 {len(images)} 张图片")
            # 保存第一张图片作为测试
            save_test_image(images[0], "test_connection")
            return True
        else:
            print("⚠ API调用成功，但未返回图片")
            return False
            
    except Exception as e:
        print(f"✗ API调用异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Gemini API 测试工具")
    print("="*60)
    print(f"输出目录: {TEST_OUTPUT_DIR.absolute()}")
    
    results = {}
    
    # 测试0.5: 代理连接（如果配置了代理）
    results['proxy'] = await test_proxy_connection()
    
    # 测试0: API连接
    results['connection'] = await test_api_connection()
    
    if not results['connection']:
        print("\n" + "="*60)
        print("⚠ API连接测试失败，跳过后续测试")
        print("="*60)
        return
    
    # 测试1: 文本生成图片
    results['text_to_image'] = await test_text_to_image()
    
    # 测试2: 图片生成图片（可选）
    results['image_to_image'] = await test_image_to_image()
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    if results.get('proxy') is not None:
        print(f"代理连接: {'✓ 通过' if results['proxy'] else '✗ 失败'}")
    print(f"API连接: {'✓ 通过' if results['connection'] else '✗ 失败'}")
    print(f"文本生成图片: {'✓ 通过' if results.get('text_to_image') else '✗ 失败'}")
    if results.get('image_to_image') is not None:
        print(f"图片生成图片: {'✓ 通过' if results['image_to_image'] else '✗ 失败'}")
    else:
        print(f"图片生成图片: ⚠ 跳过（未提供测试图片）")
    
    print(f"\n所有测试结果已保存到: {TEST_OUTPUT_DIR.absolute()}")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


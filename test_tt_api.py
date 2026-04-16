#!/usr/bin/env python3
"""
TT API 测试脚本
用于测试TT API调用是否成功，以及能否正确捕获生成的图片
"""

import os
import asyncio
import base64
from pathlib import Path
from dotenv import load_dotenv
from tt_api import call_tt_api

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


async def test_api_connection():
    """测试API连接和基本功能"""
    print("\n" + "="*60)
    print("测试 0: TT API连接测试")
    print("="*60)
    
    # 检查API Key
    api_key = os.getenv("TT_API_KEY", "9b9ece59-df55-c566-1157-1f45b7abfca9")
    if not api_key:
        print("✗ TT_API_KEY 未设置")
        print("  请在 .env 文件中设置 TT_API_KEY，或使用默认值")
        return False
    
    print(f"✓ API Key 已配置 (长度: {len(api_key)} 字符)")
    if api_key == "9b9ece59-df55-c566-1157-1f45b7abfca9":
        print("  使用默认API Key")
    else:
        print("  使用环境变量中的API Key")
    
    # 测试简单调用
    print("\n测试简单API调用...")
    simple_prompt = "Generate a simple red circle on white background"
    try:
        images, error = await call_tt_api([], simple_prompt)
        
        if error:
            print(f"✗ API调用失败: {error}")
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


async def test_text_to_image():
    """测试文本生成图片"""
    print("\n" + "="*60)
    print("测试 1: 文本生成图片")
    print("="*60)
    
    prompt = "Generate a beautiful sunset landscape with mountains and a lake"
    print(f"提示词: {prompt}")
    
    try:
        images, error = await call_tt_api([], prompt)
        
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


async def test_makeup_style():
    """测试妆容风格提示词"""
    print("\n" + "="*60)
    print("测试 2: 妆容风格生成")
    print("="*60)
    
    prompt = "Generate a photo showing the person in the input image with a new makeup style applied. The transformation should maintain the person's facial features and identity while changing only their makeup, including eyeshadow, lipstick, foundation, blush, contouring, highlighting, and other cosmetic elements. Create a realistic and natural-looking image with the new makeup that enhances the person's natural beauty and suits their face shape and features. Apply natural nude makeup style, including light foundation, brown eyeshadow, natural blush, and nude lipstick, maintaining their facial features and natural appearance."
    print(f"提示词: {prompt[:100]}...")
    
    try:
        images, error = await call_tt_api([], prompt)
        
        if error:
            print(f"✗ 调用失败: {error}")
            return False
        
        if images and len(images) > 0:
            print(f"✓ 成功生成 {len(images)} 张图片")
            for i, img_data in enumerate(images):
                save_test_image(img_data, f"test_makeup_style_{i+1}")
            return True
        else:
            print("✗ 未生成图片")
            return False
            
    except Exception as e:
        print(f"✗ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_endpoint():
    """测试API端点是否可访问"""
    print("\n" + "="*60)
    print("测试 -1: API端点连通性测试")
    print("="*60)
    
    try:
        import httpx
        endpoint = "https://api.ttapi.io/gemini/image/generate"
        
        print(f"测试端点: {endpoint}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 尝试发送一个简单的请求（可能会失败，但可以测试连接）
            try:
                # 发送一个最小请求测试连接
                headers = {
                    "TT-API-KEY": os.getenv("TT_API_KEY", "9b9ece59-df55-c566-1157-1f45b7abfca9"),
                    "Content-Type": "application/json"
                }
                payload = {
                    "prompt": "test",
                    "mode": "gemini-2.5-flash-image-preview"
                }
                
                response = await client.post(endpoint, json=payload, headers=headers, timeout=10.0)
                print(f"✓ 端点可访问 (状态码: {response.status_code})")
                
                if response.status_code == 200:
                    print("✓ API端点响应正常")
                    return True
                elif response.status_code == 401:
                    print("✗ API Key认证失败，请检查API Key是否正确")
                    return False
                elif response.status_code == 400:
                    print("⚠ API端点可访问，但请求格式可能有问题（这是正常的，因为我们只是测试连接）")
                    return True
                else:
                    print(f"⚠ API端点返回状态码: {response.status_code}")
                    print(f"  响应内容: {response.text[:200]}")
                    return True  # 至少端点是可以访问的
                    
            except httpx.ConnectError as e:
                print(f"✗ 无法连接到API端点: {str(e)}")
                print("  可能原因:")
                print("    1. 网络连接问题")
                print("    2. API端点地址错误")
                print("    3. 防火墙阻止连接")
                return False
            except httpx.TimeoutException as e:
                print(f"✗ 连接超时: {str(e)}")
                return False
            except Exception as e:
                print(f"⚠ 连接测试异常: {str(e)}")
                return False
                
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("TT API 测试工具")
    print("="*60)
    print(f"输出目录: {TEST_OUTPUT_DIR.absolute()}")
    
    results = {}
    
    # 测试-1: API端点连通性
    results['endpoint'] = await test_api_endpoint()
    
    # 测试0: API连接
    results['connection'] = await test_api_connection()
    
    if not results['connection']:
        print("\n" + "="*60)
        print("⚠ API连接测试失败，跳过后续测试")
        print("="*60)
        return
    
    # 测试1: 文本生成图片
    results['text_to_image'] = await test_text_to_image()
    
    # 测试2: 妆容风格生成
    results['makeup_style'] = await test_makeup_style()
    
    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    if results.get('endpoint') is not None:
        print(f"API端点连通: {'✓ 通过' if results['endpoint'] else '✗ 失败'}")
    print(f"API连接: {'✓ 通过' if results['connection'] else '✗ 失败'}")
    print(f"文本生成图片: {'✓ 通过' if results.get('text_to_image') else '✗ 失败'}")
    print(f"妆容风格生成: {'✓ 通过' if results.get('makeup_style') else '✗ 失败'}")
    
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


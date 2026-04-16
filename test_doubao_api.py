#!/usr/bin/env python3
"""
豆包API测试脚本
测试豆包API的图片生成功能
"""

import os
import asyncio
import base64
from dotenv import load_dotenv
from doubao_api import call_doubao_api

# 加载环境变量
load_dotenv()


async def test_with_local_image():
    """使用本地图片文件进行测试"""
    print("\n" + "="*60)
    print("测试4: 使用本地图片文件（需要IMGBB_API_KEY）")
    print("="*60)
    
    # 检查是否配置了IMGBB_API_KEY
    if not os.getenv("IMGBB_API_KEY"):
        print("⚠️  跳过此测试: 未配置IMGBB_API_KEY环境变量")
        return None
    
    # 尝试读取测试图片文件
    test_image_path = "test.png"  # 可以修改为实际的测试图片路径
    
    if not os.path.exists(test_image_path):
        print(f"⚠️  跳过此测试: 测试图片文件不存在 ({test_image_path})")
        print("   提示: 可以创建一个测试图片文件，或修改test_image_path变量")
        return None
    
    try:
        # 读取图片并转换为base64
        with open(test_image_path, "rb") as f:
            image_bytes = f.read()
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{base64_str}"
        
        prompt = "将这张图片转换为卡通风格，色彩更鲜艳"
        
        print(f"输入图片: {test_image_path} ({len(image_bytes)} bytes)")
        print(f"提示词: {prompt}")
        print("开始调用豆包API（将上传到imgbb）...")
        
        images, error = await call_doubao_api([data_url], prompt)
        
        if error:
            print(f"❌ 测试失败: {error}")
            return False
        elif images:
            print(f"✅ 测试成功！生成了 {len(images)} 张图片")
            print(f"第一张图片的base64长度: {len(images[0])} 字符")
            return True
        else:
            print("❌ 测试失败: 未返回图片")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("豆包API测试脚本")
    print("="*60)
    
    # 检查环境变量
    if not os.getenv("ARK_API_KEY"):
        print("❌ 错误: 未设置ARK_API_KEY环境变量")
        print("   请在.env文件中设置: ARK_API_KEY=your_api_key")
        return
    
    print("✅ ARK_API_KEY已配置")
    
    if os.getenv("IMGBB_API_KEY"):
        print("✅ IMGBB_API_KEY已配置（支持base64图片上传）")
    else:
        print("⚠️  IMGBB_API_KEY未配置（将使用纯文本生成模式）")
    
    # 运行测试
    results = []
    
    # 测试4: 使用本地图片文件
    result4 = await test_with_local_image()
    if result4 is not None:
        results.append(("本地图片生成", result4))
    
    # 输出测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for test_name, result in results:
        if result is None:
            status = "⏭️  跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{test_name}: {status}")
    
    # 统计
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过")
    
    if passed > 0:
        print("\n✅ 至少有一个测试通过，豆包API可以正常工作！")
    else:
        print("\n❌ 所有测试都失败，请检查配置和网络连接")


if __name__ == "__main__":
    asyncio.run(main())

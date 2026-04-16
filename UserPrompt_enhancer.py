import httpx
import json
import asyncio
from typing import Optional

class OllamaPromptEnhancer:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model_name = "deepseek-r1:7b" 
        self.timeout = 60.0  # 增加超时时间，因为R1模型推理可能较慢
        
    async def check_ollama_availability(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def enhance_prompt(self, user_prompt: str, max_retries: int = 2) -> str:
        """
        使用Ollama的DeepSeek-R1模型增强提示词
        
        Args:
            user_prompt: 用户原始提示词
            max_retries: 最大重试次数
            
        Returns:
            str: 增强后的提示词
        """
        # 检查Ollama服务
        if not await self.check_ollama_availability():
            print("[Ollama] 服务不可用，使用原始提示词")
            return user_prompt
        
        # 系统提示词，专门优化用于图像生成的提示词
        system_prompt = """你是一个专业的人物形象设计AI提示词优化专家。专门优化人物发型、妆容、风格和外观描述的提示词。请根据用户的简单描述，生成详细、专业、高质量的英文提示词。

优化原则：
1. 保持原始意图，但丰富人物形象细节：发型、发色、妆容、服饰、配饰等
2. 添加合适的人物风格：时尚、复古、日常、正式、休闲、派对等
3. 包含专业的美妆元素：眼妆、唇妆、底妆、腮红等具体描述
4. 详细描述发型细节：长度、卷度、颜色、造型等
5. 使用英文逗号分隔的标签形式，不要使用句子
6. 确保提示词具体、可执行，适合AI图像生成
7. 长度控制在50个单词之内
8. 专注于人物形象，避免过多环境描述

优秀示例：
输入："换个发型"
输出："beautiful woman with stylish layered bob haircut, caramel balayage hair color, soft waves, face-framing layers, glossy hair texture, natural makeup with subtle smoky eyes, nude lipstick, dewy foundation, professional hairstyling, studio lighting, portrait photography, high fashion look, 8K resolution"

输入："日常妆容"
输出："young Asian woman, fresh daily makeup, light foundation, natural eyebrow shaping, soft pink blush, subtle eyeshadow with shimmer, defined eyeliner, glossy lip balm, hair in loose waves, casual outfit, soft natural lighting, clean skin texture, minimalistic style, lifestyle portrait"

输入："复古风格"
输出："elegant woman in 1920s vintage style, finger wave hairstyle, dark marcel waves, deep red lipstick, smokey kohl-rimmed eyes, pale matte complexion, flapper headpiece with feathers, art deco jewelry, black and white photography, dramatic studio lighting, high contrast, classic Hollywood glamour"

请直接返回优化后的英文提示词，不要额外解释。"""

        # 构建请求数据
        request_data = {
            "model": self.model_name,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 500
            }
        }
        
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=request_data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        enhanced_prompt = result.get("response", "").strip()
                        
                        # 清理响应内容，移除可能的额外解释
                        enhanced_prompt = self._clean_response(enhanced_prompt)
                        
                        if enhanced_prompt and len(enhanced_prompt) > len(user_prompt):
                            print(f"[Ollama] 提示词增强成功")
                            print(f"[Ollama] 原始: {user_prompt}")
                            print(f"[Ollama] 增强: {enhanced_prompt}")
                            return enhanced_prompt
                        else:
                            print(f"[Ollama] 增强结果不理想，使用原始提示词")
                            return user_prompt
                    else:
                        print(f"[Ollama] API请求失败，状态码: {response.status_code}")
                        
            except httpx.TimeoutException:
                print(f"[Ollama] 请求超时 (尝试 {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
            except Exception as e:
                print(f"[Ollama] 增强失败: {str(e)} (尝试 {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue
        
        print("[Ollama] 所有重试失败，使用原始提示词")
        return user_prompt
    
    def _clean_response(self, response: str) -> str:
        """清理LLM响应，移除可能的额外解释"""
        # 移除常见的开头短语
        phrases_to_remove = [
            "优化后的提示词：", "Enhanced prompt:", "Here is the enhanced prompt:",
            "改进的提示词：", "Based on your input, here is the enhanced prompt:",
            "当然，", "好的，", "Here you go:", "Sure, here is the enhanced prompt:"
        ]
        
        cleaned = response
        for phrase in phrases_to_remove:
            if cleaned.startswith(phrase):
                cleaned = cleaned[len(phrase):].strip()
        
        # 如果包含引号，提取引号内的内容
        if '"' in cleaned:
            import re
            quoted = re.findall(r'"([^"]*)"', cleaned)
            if quoted:
                cleaned = quoted[0]
        
        # 移除可能的中文解释部分（如果模型不小心添加了）
        lines = cleaned.split('\n')
        if len(lines) > 1:
            # 取第一行，通常是最主要的提示词
            cleaned = lines[0].strip()
        
        return cleaned

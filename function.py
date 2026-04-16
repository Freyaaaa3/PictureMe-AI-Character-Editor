"""
功能管理模块
定义不同功能的系统提示词和处理逻辑
"""

# 功能定义
FUNCTIONS = {
    "time_traveler": {
        "name": "时间穿越",
        "name_en": "Time Traveler",
        "description": "穿越时空，体验不同年代的风采",
        "system_prompt": "Generate a photo showing the person in the input image transformed to different historical decades. The transformation should maintain the person's facial features and identity while adapting their clothing, hairstyle, and overall appearance to match the style of the chosen decade. Create a realistic and natural-looking image that seamlessly blends the person into the historical period.",
        "default_prompt": "Transform the person in the image to look like they are from the {decade} era, maintaining their facial features while adapting their appearance to match the historical style."
    },
    "hair_style": {
        "name": "发型设计",
        "name_en": "Hair Style",
        "description": "尝试新发型和发色",
        "system_prompt": "Generate a photo showing the person in the input image with a new hairstyle and/or hair color. The transformation should maintain the person's facial features and identity while changing only their hair. Create a realistic and natural-looking image with the new hairstyle that suits the person's face shape and features.",
        "default_prompt": "Change the person's hairstyle to {hairstyle} and hair color to {color}, maintaining their facial features and overall appearance."
    },
    "style_lookbook": {
        "name": "风格照片",
        "name_en": "Style Lookbook",
        "description": "您的个人时尚大片",
        "system_prompt": "Generate a professional fashion photoshoot image showing the person in the input image wearing stylish clothing and accessories. The image should look like a high-quality fashion magazine photo with good lighting, composition, and styling. Maintain the person's facial features while creating a fashionable and trendy look that showcases different clothing styles and poses.",
        "default_prompt": "Create a professional fashion photoshoot image of the person wearing {style_description}, with professional lighting and styling, maintaining their facial features."
    },
    "makeup_style": {
        "name": "妆容风格",
        "name_en": "Makeup Style",
        "description": "尝试不同风格的妆容效果",
        "system_prompt": "Generate a photo showing the person in the input image with a new makeup style applied. The transformation should maintain the person's facial features and identity while changing only their makeup, including eyeshadow, lipstick, foundation, blush, contouring, highlighting, and other cosmetic elements. Create a realistic and natural-looking image with the new makeup that enhances the person's natural beauty and suits their face shape and features. The makeup should be professionally applied with attention to detail, proper blending, and realistic textures.",
        "default_prompt": "Apply {makeup_style} makeup style to the person, including {makeup_details}, maintaining their facial features and natural appearance."
    }
}


def get_function(function_id):
    """
    获取指定功能的配置信息
    
    Args:
        function_id: 功能ID (time_traveler, hair_style, style_lookbook, makeup_style)
    
    Returns:
        dict: 功能配置信息，如果不存在则返回None
    """
    return FUNCTIONS.get(function_id)


def get_all_functions():
    """
    获取所有功能列表
    
    Returns:
        dict: 所有功能配置
    """
    return FUNCTIONS


def get_system_prompt(function_id):
    """
    获取指定功能的系统提示词
    
    Args:
        function_id: 功能ID
    
    Returns:
        str: 系统提示词，如果功能不存在则返回None
    """
    func = get_function(function_id)
    if func:
        return func.get("system_prompt", "")
    return None


def combine_prompts(system_prompt, user_prompt=None):
    """
    合并系统提示词和用户提示词
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户输入的提示词（可选）
    
    Returns:
        str: 合并后的提示词
    """
    if user_prompt and user_prompt.strip():
        # 如果用户提供了提示词，将两者合并
        return f"{system_prompt} {user_prompt.strip()}"
    else:
        # 如果用户没有提供提示词，只使用系统提示词
        return system_prompt

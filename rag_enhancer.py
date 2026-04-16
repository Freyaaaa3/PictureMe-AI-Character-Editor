"""
检索增强生成（RAG）模块
使用Ollama embedding模型进行向量化存储和检索，对用户输入的提示词进行增强
"""

import os
import json
import numpy as np
from typing import List, Tuple, Optional
from pathlib import Path

try:
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.llms import Ollama
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False
    print("警告: langchain-community未安装，将使用简单的文本匹配。运行: pip install langchain-community")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# 提示词库文件路径
PROMPT_FILES = {
    "time_traveler": "prompts_time_traveler.json",
    "hair_style": "prompts_hair_style.json",
    "style_lookbook": "prompts_style_lookbook.json",
    "makeup_style": "prompts_makeup_style.json"
}

# 每个功能对应的JSON键名
PROMPT_JSON_KEYS = {
    "time_traveler": "era_transformation_prompts",
    "hair_style": "hairstyle_transformation_prompts",
    "style_lookbook": "photo_style_portrait_prompts",
    "makeup_style": "makeup_style_prompts"
}

# 向量缓存目录
VECTOR_CACHE_DIR = Path("vector_cache")
VECTOR_CACHE_DIR.mkdir(exist_ok=True)

# Ollama配置
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "deepseek-r1:7b")


def check_ollama_models() -> List[str]:
    """
    检查Ollama中可用的模型
    
    Returns:
        List[str]: 可用模型列表
    """
    if not HTTPX_AVAILABLE:
        return []
    
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = [model.get("name", "") for model in data.get("models", [])]
            return [m for m in models if m]
    except Exception as e:
        print(f"检查Ollama模型失败: {e}")
    
    return []


def get_available_embedding_model() -> Optional[str]:
    """
    获取可用的embedding模型
    
    Returns:
        Optional[str]: 模型名称，如果不可用则返回None
    """
    available_models = check_ollama_models()
    
    if not available_models:
        print("未检测到Ollama模型，请确保Ollama服务正在运行")
        return None
    
    print(f"检测到Ollama模型: {', '.join(available_models)}")
    
    # 优先使用配置的模型
    if OLLAMA_EMBEDDING_MODEL in available_models:
        print(f"使用配置的embedding模型: {OLLAMA_EMBEDDING_MODEL}")
        return OLLAMA_EMBEDDING_MODEL
    
    # 尝试查找包含embedding关键词的模型
    embedding_models = [m for m in available_models if 'embed' in m.lower() or 'r1' in m.lower()]
    if embedding_models:
        model = embedding_models[0]
        print(f"使用检测到的embedding模型: {model}")
        return model
    
    # 如果都没有，使用第一个模型
    if available_models:
        model = available_models[0]
        print(f"使用第一个可用模型: {model}")
        return model
    
    return None


class VectorStore:
    """向量存储和检索类（使用Ollama）"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化向量存储
        
        Args:
            model_name: embedding模型名称，如果为None则自动检测
        """
        self.model_name = model_name or get_available_embedding_model()
        self.embeddings = None
        self.embeddings_cache = {}
        
        if EMBEDDING_AVAILABLE and self.model_name:
            try:
                print(f"初始化Ollama embedding模型: {self.model_name}")
                self.embeddings = OllamaEmbeddings(
                    model=self.model_name,
                    base_url=OLLAMA_BASE_URL
                )
                # 测试连接
                test_embedding = self.embeddings.embed_query("test")
                if test_embedding:
                    print(f"Ollama embedding模型初始化成功，向量维度: {len(test_embedding)}")
                else:
                    print("警告: embedding模型测试失败")
                    self.embeddings = None
            except Exception as e:
                print(f"初始化Ollama embedding模型失败: {e}")
                self.embeddings = None
        else:
            if not EMBEDDING_AVAILABLE:
                print("langchain-community未安装，无法使用embedding功能")
            elif not self.model_name:
                print("未找到可用的embedding模型")
            self.embeddings = None
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        获取文本的embedding向量
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[np.ndarray]: embedding向量
        """
        if not text or not text.strip():
            return None
        
        if not self.embeddings:
            return None
        
        # 检查缓存
        cache_key = text.lower().strip()
        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]
        
        try:
            embedding = self.embeddings.embed_query(text)
            if embedding:
                embedding_array = np.array(embedding)
                self.embeddings_cache[cache_key] = embedding_array
                return embedding_array
        except Exception as e:
            print(f"生成embedding失败: {e}")
            return None
        
        return None
    
    def get_embeddings_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        批量获取文本的embedding向量
        
        Args:
            texts: 文本列表
            
        Returns:
            Optional[np.ndarray]: embedding向量矩阵
        """
        if not texts or not self.embeddings:
            return None
        
        try:
            embeddings = self.embeddings.embed_documents(texts)
            if embeddings:
                return np.array(embeddings)
        except Exception as e:
            print(f"批量生成embedding失败: {e}")
            return None
        
        return None
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 相似度分数（0-1）
        """
        if vec1 is None or vec2 is None:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class PromptVectorStore:
    """提示词向量存储类"""
    
    def __init__(self, function_id: str):
        """
        初始化提示词向量存储
        
        Args:
            function_id: 功能ID
        """
        self.function_id = function_id
        self.prompts = []  # 存储用于向量化的文本（detailed_prompt）
        self.prompt_objects = []  # 存储完整的提示词对象
        self.embeddings = None
        self.vector_store = VectorStore()
        self.load_prompts()
    
    def _chunk_text(self, text: str, max_chunk_length: int = 200) -> List[str]:
        """
        将长文本切分成更小的chunks用于向量化
        优先按语义单位（句子）切分，保持语义完整性
        
        Args:
            text: 输入文本
            max_chunk_length: 每个chunk的最大长度（字符数）
            
        Returns:
            List[str]: 切分后的文本列表
        """
        if not text or not text.strip():
            return []
        
        if len(text) <= max_chunk_length:
            return [text.strip()]
        
        chunks = []
        # 按句子切分（中文句号、英文句号、逗号等）
        import re
        # 使用更精确的中文标点符号分割
        sentences = re.split(r'[。，,\.\n；;]', text)
        
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 如果当前chunk加上新句子不超过限制，则合并
            if len(current_chunk) + len(sentence) + 1 <= max_chunk_length:
                if current_chunk:
                    current_chunk += "，" + sentence
                else:
                    current_chunk = sentence
            else:
                # 保存当前chunk，开始新chunk
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个句子就超过限制，强制切分
                if len(sentence) > max_chunk_length:
                    # 按字符数强制切分
                    for i in range(0, len(sentence), max_chunk_length):
                        chunks.append(sentence[i:i + max_chunk_length])
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text.strip()]
    
    def load_prompts(self):
        """从JSON文件加载提示词"""
        prompt_file = PROMPT_FILES.get(self.function_id)
        if not prompt_file:
            print(f"未找到功能 {self.function_id} 的提示词文件")
            return
        
        file_path = Path(prompt_file)
        if not file_path.exists():
            print(f"提示词文件不存在: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取对应的JSON键名
            json_key = PROMPT_JSON_KEYS.get(self.function_id)
            if not json_key:
                # 如果找不到键名，尝试自动检测（取第一个键，排除metadata）
                keys = [k for k in data.keys() if k != 'metadata'] if isinstance(data, dict) else []
                json_key = keys[0] if keys else None
            
            if json_key and json_key in data:
                prompt_list = data[json_key]
                # 提取detailed_prompt字段用于向量化
                self.prompt_objects = prompt_list
                self.prompts = []
                
                for item in prompt_list:
                    if isinstance(item, dict):
                        # 使用detailed_prompt进行向量化（完整信息，更准确）
                        detailed_prompt = item.get('detailed_prompt', '')
                        
                        # 如果没有detailed_prompt，则使用description和key_elements组合
                        if not detailed_prompt:
                            description = item.get('description', '')
                            key_elements = item.get('key_elements', [])
                            era = item.get('era') or item.get('style_name', '')
                            detailed_prompt = f"{era} {description} {' '.join(key_elements)}"
                        
                        # 将detailed_prompt切分成chunks用于向量化
                        chunks = self._chunk_text(detailed_prompt, max_chunk_length=200)
                        self.prompts.extend(chunks)
                        
                        # 保存原始对象和对应的chunk索引映射
                        if not hasattr(self, 'chunk_to_object'):
                            self.chunk_to_object = {}
                        for chunk in chunks:
                            if chunk not in self.chunk_to_object:
                                self.chunk_to_object[chunk] = item
                    elif isinstance(item, str):
                        # 兼容旧格式（直接是字符串）
                        chunks = self._chunk_text(item, max_chunk_length=150)
                        self.prompts.extend(chunks)
                        obj = {"detailed_prompt": item}
                        self.prompt_objects.append(obj)
                        if not hasattr(self, 'chunk_to_object'):
                            self.chunk_to_object = {}
                        for chunk in chunks:
                            if chunk not in self.chunk_to_object:
                                self.chunk_to_object[chunk] = obj
                
                print(f"加载了 {len(self.prompt_objects)} 个提示词对象，切分为 {len(self.prompts)} 个chunks从 {prompt_file} (键: {json_key})")
            else:
                # 兼容旧格式（直接是数组）
                if isinstance(data, list):
                    self.prompts = []
                    self.prompt_objects = []
                    if not hasattr(self, 'chunk_to_object'):
                        self.chunk_to_object = {}
                    for item in data:
                        chunks = self._chunk_text(item, max_chunk_length=150)
                        self.prompts.extend(chunks)
                        obj = {"detailed_prompt": item}
                        self.prompt_objects.append(obj)
                        for chunk in chunks:
                            if chunk not in self.chunk_to_object:
                                self.chunk_to_object[chunk] = obj
                    print(f"加载了 {len(self.prompts)} 个提示词从 {prompt_file} (旧格式)")
                else:
                    print(f"提示词文件格式不正确: {prompt_file}")
                    self.prompts = []
                    self.prompt_objects = []
            
            # 尝试加载缓存的embeddings，如果没有则计算
            if self.prompts and not self._load_cache():
                self._precompute_embeddings()
        except Exception as e:
            print(f"加载提示词文件失败: {e}")
            import traceback
            traceback.print_exc()
            self.prompts = []
            self.prompt_objects = []
    
    def _precompute_embeddings(self):
        """预计算所有提示词的embeddings"""
        if not self.prompts or not self.vector_store.embeddings:
            print("无法预计算embeddings：提示词为空或embedding模型不可用")
            return
        
        try:
            print(f"开始预计算 {len(self.prompts)} 个提示词的embeddings...")
            self.embeddings = self.vector_store.get_embeddings_batch(self.prompts)
            
            if self.embeddings is not None:
                print(f"Embeddings预计算完成，形状: {self.embeddings.shape}")
                # 保存到缓存
                self._save_cache()
            else:
                print("预计算embeddings失败")
        except Exception as e:
            print(f"预计算embeddings失败: {e}")
            self.embeddings = None
    
    def _save_cache(self):
        """保存embeddings到缓存文件"""
        if self.embeddings is None:
            return
        
        cache_file = VECTOR_CACHE_DIR / f"{self.function_id}_embeddings.npy"
        metadata_file = VECTOR_CACHE_DIR / f"{self.function_id}_metadata.json"
        
        try:
            # 保存embeddings
            np.save(cache_file, self.embeddings)
            
            # 保存元数据（包括模型名称和提示词列表）
            metadata = {
                "model_name": self.vector_store.model_name,
                "prompts": self.prompts,  # 保存用于向量化的文本列表
                "prompt_objects": self.prompt_objects,  # 保存完整的对象信息
                "embeddings_shape": list(self.embeddings.shape)
            }
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"向量缓存已保存到: {cache_file}")
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def _load_cache(self) -> bool:
        """从缓存文件加载embeddings"""
        cache_file = VECTOR_CACHE_DIR / f"{self.function_id}_embeddings.npy"
        metadata_file = VECTOR_CACHE_DIR / f"{self.function_id}_metadata.json"
        
        if not cache_file.exists() or not metadata_file.exists():
            print(f"缓存文件不存在，需要重新计算embeddings")
            return False
        
        try:
            # 加载元数据
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 检查模型是否匹配
            cached_model = metadata.get("model_name")
            current_model = self.vector_store.model_name
            
            if cached_model != current_model:
                print(f"缓存模型 ({cached_model}) 与当前模型 ({current_model}) 不匹配，需要重新计算")
                return False
            
            # 检查提示词是否匹配
            cached_prompts = metadata.get("prompts", [])
            if cached_prompts != self.prompts:
                print("提示词已更新，需要重新计算embeddings")
                return False
            
            # 恢复完整的提示词对象信息
            cached_objects = metadata.get("prompt_objects", [])
            if cached_objects:
                self.prompt_objects = cached_objects
            
            # 加载embeddings
            self.embeddings = np.load(cache_file)
            print(f"从缓存加载了 {len(self.embeddings)} 个embeddings，形状: {self.embeddings.shape}")
            return True
        except Exception as e:
            print(f"加载缓存失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 3, threshold: float = 0.15) -> List[Tuple[dict, float]]:
        """
        使用向量相似度搜索相关提示词（纯向量匹配）
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            threshold: 相似度阈值
            
        Returns:
            List[Tuple[dict, float]]: (提示词对象, 相似度分数) 列表
        """
        if not query or not query.strip() or not self.prompts:
            return []
        
        # 如果embeddings未计算，尝试从缓存加载
        if self.embeddings is None:
            if not self._load_cache():
                # 如果缓存也没有，重新计算
                self._precompute_embeddings()
        
        # 如果还是没有embeddings，无法进行向量检索
        if self.embeddings is None:
            print("警告: 无法使用向量检索，embeddings不可用")
            return []
        
        # 获取查询的embedding向量
        query_embedding = self.vector_store.get_embedding(query)
        if query_embedding is None:
            print("警告: 无法生成查询embedding向量")
            return []
        
        # 计算所有chunks与查询向量的相似度
        chunk_similarities = []
        for i, prompt_chunk in enumerate(self.prompts):
            # 计算余弦相似度
            similarity = self.vector_store.cosine_similarity(
                query_embedding,
                self.embeddings[i]
            )
            
            # 只保留超过阈值的相似度
            if similarity >= threshold:
                # 获取对应的完整对象
                obj = getattr(self, 'chunk_to_object', {}).get(prompt_chunk)
                if not obj:
                    # 如果没有映射，尝试从prompt_objects中找到对应的对象
                    # 根据chunk索引推断对象索引
                    if self.prompt_objects:
                        chunks_per_obj = max(1, len(self.prompts) // len(self.prompt_objects))
                        obj_idx = i // chunks_per_obj
                        if obj_idx < len(self.prompt_objects):
                            obj = self.prompt_objects[obj_idx]
                        else:
                            obj = self.prompt_objects[-1]  # 使用最后一个对象
                    else:
                        obj = {}
                
                chunk_similarities.append((obj, float(similarity), prompt_chunk))
        
        # 按对象去重，保留每个对象的最高相似度分数
        object_scores = {}
        for obj, score, chunk in chunk_similarities:
            # 使用era或style_name作为唯一标识
            obj_key = str(obj.get('era') or obj.get('style_name') or obj.get('detailed_prompt', ''))
            if obj_key not in object_scores or score > object_scores[obj_key][1]:
                object_scores[obj_key] = (obj, score)
        
        # 按相似度排序并返回前k个
        results = sorted(object_scores.values(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(obj, score) for obj, score in results]
    
    def _keyword_match(self, query: str, objects: List[dict]) -> List[Tuple[dict, float]]:
        """
        关键词匹配（用于快速筛选和提升相关性）
        
        Args:
            query: 查询文本
            objects: 提示词对象列表
            
        Returns:
            List[Tuple[dict, float]]: (对象, 匹配分数) 列表
        """
        query_lower = query.lower()
        results = []
        
        # 定义关键词映射（提升匹配准确性）
        keyword_mapping = {
            '未来': ['未来', '未来主义', '22世纪', '高科技', '科幻', '全息', '飞行汽车'],
            '过去': ['过去', '历史', '古代', '复古', 'vintage'],
            '史前': ['史前', '石器', '原始', '恐龙', '洞穴'],
            '中世纪': ['中世纪', '骑士', '城堡', '欧洲'],
            '文艺复兴': ['文艺复兴', '达芬奇', '拉斐尔', '古典'],
            '1920': ['1920', '爵士', '装饰艺术', 'flapper'],
            '1950': ['1950', '复古', '经典汽车', 'A字裙'],
            '1980': ['1980', '霓虹', '迪斯科', '合成器'],
            '1990': ['1990', '格朗基', 'grunge', '破旧']
        }
        
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            
            score = 0.0
            era = obj.get('era', '').lower()
            style_name = obj.get('style_name', '').lower()
            description = obj.get('description', '').lower()
            key_elements = [e.lower() for e in obj.get('key_elements', [])]
            
            # 检查直接匹配
            search_text = f"{era} {style_name} {description} {' '.join(key_elements)}"
            
            # 检查关键词映射
            for keyword, synonyms in keyword_mapping.items():
                if keyword in query_lower:
                    for synonym in synonyms:
                        if synonym in search_text:
                            score += 0.5  # 关键词匹配加分
                            break
            
            # 检查直接包含
            if query_lower in search_text or any(word in search_text for word in query_lower.split()):
                score += 0.3
            
            # 检查字符重叠
            query_chars = set(query_lower)
            text_chars = set(search_text)
            common_chars = len(query_chars & text_chars)
            if common_chars > 0:
                score += common_chars / max(len(query_chars), len(text_chars)) * 0.2
            
            if score > 0.1:
                results.append((obj, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _simple_search(self, query: str, top_k: int = 3) -> List[Tuple[dict, float]]:
        """
        简单的文本匹配搜索（仅作为向量检索失败时的备选方案）
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            
        Returns:
            List[Tuple[dict, float]]: (提示词对象, 相似度分数) 列表
        """
        # 仅作为备选方案，不主动使用
        # 如果向量检索可用，应该使用向量检索
        results = []
        query_lower = query.lower()
        
        for obj in self.prompt_objects:
            if not isinstance(obj, dict):
                continue
            
            # 简单的文本包含检查
            era = obj.get('era', '').lower()
            style_name = obj.get('style_name', '').lower()
            description = obj.get('description', '').lower()
            search_text = f"{era} {style_name} {description}".lower()
            
            # 计算简单的字符重叠度
            query_chars = set(query_lower)
            text_chars = set(search_text)
            common_chars = len(query_chars & text_chars)
            total_chars = len(query_chars | text_chars)
            
            if total_chars > 0:
                similarity = common_chars / total_chars
                if similarity > 0.1:
                    results.append((obj, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# 全局向量存储实例（按功能ID缓存）
_vector_stores = {}


def get_vector_store(function_id: str) -> PromptVectorStore:
    """
    获取或创建指定功能的向量存储实例
    
    Args:
        function_id: 功能ID
        
    Returns:
        PromptVectorStore: 向量存储实例
    """
    if function_id not in _vector_stores:
        _vector_stores[function_id] = PromptVectorStore(function_id)
    return _vector_stores[function_id]


def enhance_prompt(user_prompt: str, function_id: str,
                  system_prompt: Optional[str] = None,
                  top_k: int = 1,
                  similarity_threshold: float = 0.2) -> str:
    """
    使用向量检索增强用户提示词（智能合并，返回中文）
    
    Args:
        user_prompt: 用户输入的提示词
        function_id: 功能ID
        system_prompt: 系统提示词（可选）
        top_k: 检索前k个相关提示词（默认1个，避免过长）
        similarity_threshold: 相似度阈值（降低以提高召回率）
        
    Returns:
        str: 增强后的提示词（中文）
    """
    if not user_prompt or not user_prompt.strip():
        return system_prompt or ""
    
    # 获取向量存储
    vector_store = get_vector_store(function_id)
    
    # 检索相关提示词
    print(f"\n{'='*60}")
    print(f"RAG检索增强 - 功能: {function_id}")
    print(f"用户提示词: {user_prompt}")
    print(f"{'='*60}")
    
    relevant_objects = vector_store.search(
        user_prompt,
        top_k=top_k,
        threshold=similarity_threshold
    )
    
    # 打印匹配结果
    if relevant_objects:
        print(f"\n找到 {len(relevant_objects)} 个相关提示词:")
        for i, (obj, score) in enumerate(relevant_objects, 1):
            era = obj.get('era', '')
            style_name = obj.get('style_name', '')
            description = obj.get('description', '')
            name = era or style_name or description or f"提示词{i}"
            print(f"  [{i}] 相似度: {score:.3f} - {name}")
            if description:
                print(f"      描述: {description}")
    else:
        print(f"\n未找到相似度 >= {similarity_threshold} 的相关提示词")
    
    print(f"{'='*60}\n")
    
    # 智能构建增强后的提示词
    enhanced_parts = []
    
    # 1. 添加系统提示词（如果提供）
    if system_prompt:
        enhanced_parts.append(system_prompt)
    
    # 2. 智能合并用户提示词和检索结果
    if relevant_objects:
        # 只使用最相关的一个结果（top_k=1时）
        best_obj, best_score = relevant_objects[0]
        
        # 提取关键信息构建简洁的增强提示词
        detailed_prompt = best_obj.get('detailed_prompt', '')
        
        if detailed_prompt:
            # 如果detailed_prompt太长，提取关键部分
            if len(detailed_prompt) > 300:
                # 提取前150字符和后50字符，中间用省略号
                enhanced_prompt_text = detailed_prompt[:150] + "..." + detailed_prompt[-50:]
            else:
                enhanced_prompt_text = detailed_prompt
            
            # 将用户提示词和检索到的提示词智能合并
            # 如果用户提示词已经在detailed_prompt中，直接使用detailed_prompt
            if user_prompt.strip() in detailed_prompt or len(user_prompt.strip()) < 5:
                enhanced_parts.append(enhanced_prompt_text)
            else:
                # 否则合并：用户提示词 + 检索到的关键部分
                enhanced_parts.append(f"{user_prompt.strip()}。{enhanced_prompt_text}")
        else:
            # 如果没有detailed_prompt，使用description和key_elements
            description = best_obj.get('description', '')
            key_elements = best_obj.get('key_elements', [])
            if description:
                enhanced_parts.append(f"{user_prompt.strip()}，{description}")
            elif key_elements:
                enhanced_parts.append(f"{user_prompt.strip()}，{'，'.join(key_elements[:3])}")
            else:
                enhanced_parts.append(user_prompt.strip())
    else:
        # 如果没有检索到结果，只使用用户提示词
        enhanced_parts.append(user_prompt.strip())
    
    # 合并所有部分
    enhanced_prompt = "。".join(enhanced_parts)
    
    # 限制总长度，避免过长
    max_length = 500
    if len(enhanced_prompt) > max_length:
        enhanced_prompt = enhanced_prompt[:max_length] + "..."
    
    print(f"增强后的提示词长度: {len(enhanced_prompt)} 字符")
    print(f"增强后的提示词: {enhanced_prompt}\n")
    
    return enhanced_prompt
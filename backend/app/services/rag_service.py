from __future__ import annotations

from typing import List, Dict, Any, Optional
import asyncio
import random

from app.repositories.vector_repository import (
    search_chunks,
    search_chunks_bm25,
    search_chunks_hybrid,
)
from app.core.settings import ENABLE_HYBRID_SEARCH, RAG_HYBRID_ALPHA, EMBEDDING_DIM


def embed_text(text: str) -> List[float]:
    """将文本转换为向量（占位实现）

    注意：在实际部署中，应使用真实的嵌入模型（如SiliconFlow、OpenAI等）
    这里使用随机向量作为占位，仅用于开发和测试。
    """
    # 返回随机向量（仅用于测试）
    # 在实际应用中，应该调用嵌入模型API
    return [random.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]


class RAGService:
    """RAG服务，提供检索增强生成功能"""

    def __init__(self):
        self.hybrid_enabled = ENABLE_HYBRID_SEARCH
        self.hybrid_alpha = RAG_HYBRID_ALPHA

    async def search(
        self,
        query: str,
        top_k: int = 10,
        group_ids: Optional[List[str]] = None,
        use_hybrid: Optional[bool] = None,
        alpha: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """搜索相关文档片段"""
        if use_hybrid is None:
            use_hybrid = self.hybrid_enabled

        if alpha is None:
            alpha = self.hybrid_alpha

        # 生成查询向量
        query_vector = embed_text(query)

        if use_hybrid:
            # 混合检索
            return search_chunks_hybrid(
                query_vector=query_vector,
                query_text=query,
                top_k=top_k,
                group_ids=group_ids or [],
                alpha=alpha,
            )
        else:
            # 纯向量检索
            return search_chunks(
                query_vector=query_vector,
                top_k=top_k,
                group_ids=group_ids or [],
            )

    async def search_by_vector(
        self,
        query_vector: List[float],
        top_k: int = 10,
        group_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """使用向量搜索"""
        return search_chunks(
            query_vector=query_vector,
            top_k=top_k,
            group_ids=group_ids or [],
        )

    async def search_by_text(
        self,
        query_text: str,
        top_k: int = 10,
        group_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """使用BM25全文检索"""
        return search_chunks_bm25(
            query_text=query_text,
            top_k=top_k,
            group_ids=group_ids or [],
        )

    async def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 2000,
        group_ids: Optional[List[str]] = None,
    ) -> str:
        """获取查询的上下文文本"""
        results = await self.search(
            query=query,
            top_k=10,
            group_ids=group_ids,
        )

        # 合并结果内容，直到达到最大token数
        context_parts = []
        current_length = 0

        for result in results:
            content = result.get("content", "")
            if not content:
                continue

            if current_length + len(content) > max_tokens:
                # 添加部分内容以填满剩余空间
                remaining = max_tokens - current_length
                if remaining > 100:  # 只有剩余空间足够大时才添加
                    context_parts.append(content[:remaining])
                break

            context_parts.append(content)
            current_length += len(content)

        return "\n\n".join(context_parts)

    async def test_retrieval(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """测试检索效果"""
        import time

        # 测试不同检索方法
        start_time = time.time()

        # 向量检索
        vector_results = await self.search_by_vector(
            query_vector=embed_text(query),
            top_k=5,
            group_ids=group_ids,
        )
        vector_time = time.time() - start_time

        # BM25检索
        start_time = time.time()
        bm25_results = await self.search_by_text(
            query_text=query,
            top_k=5,
            group_ids=group_ids,
        )
        bm25_time = time.time() - start_time

        # 混合检索
        start_time = time.time()
        hybrid_results = await self.search(
            query=query,
            top_k=5,
            group_ids=group_ids,
            use_hybrid=True,
        )
        hybrid_time = time.time() - start_time

        return {
            "query": query,
            "vector_results_count": len(vector_results),
            "bm25_results_count": len(bm25_results),
            "hybrid_results_count": len(hybrid_results),
            "vector_time": vector_time,
            "bm25_time": bm25_time,
            "hybrid_time": hybrid_time,
            "vector_top_titles": [r.get("file_name", "")[:50] for r in vector_results[:3]],
            "bm25_top_titles": [r.get("file_name", "")[:50] for r in bm25_results[:3]],
            "hybrid_top_titles": [r.get("file_name", "")[:50] for r in hybrid_results[:3]],
        }


# 全局RAG服务实例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """获取全局RAG服务实例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


async def ensure_rag_service() -> RAGService:
    """确保RAG服务已初始化"""
    return get_rag_service()
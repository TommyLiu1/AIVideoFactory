import os

from fastapi import Depends
from openai import OpenAI
from controllers.v1.base import new_router
from utils import utils
from utils.auth import verify_token_signature
from config.config import DeepSeek_api_url, DeepSeek_api_model
from loguru import logger

router = new_router(dependencies=[Depends(verify_token_signature)])


@router.get("/text/optimize", tags=["TextOptimize"], summary="文本优化")
async def text_optimize(user_prompt: str):
    """
    文本优化接口
    """
    optimization_instruction = """
               你是一个提示词优化专家，请优化以下用户输入的提示词，使其生成的提示词能够更好地满足生成视频的文案。
               优化后的提示词应：
               - 明确目标（如：是生成视频的文案）
               - 包含必要的细节（如：画面内容、风格、受众）
               - 避免模糊表述
               只需返回优化后的提示词，无需额外解释。
               用户提供的提示词：
               """ + user_prompt
    DeepSeek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    ai_client = OpenAI(api_key=DeepSeek_api_key, base_url=DeepSeek_api_url)
    response = ai_client.chat.completions.create(
        model=DeepSeek_api_model,
        messages=[
            {"role": "user", "content": optimization_instruction}
        ]
    )
    try:
        logger.info(f"文本优化请求成功，用户输入: {user_prompt},返回结果: {response}")
        optimized_prompt = response.choices[0].message.content
        return utils.get_response(status=200, message="文本优化成功", data={"optimized_prompt": optimized_prompt})
    except Exception as e:
        logger.error(f"文本优化请求失败: {e}")
        return utils.get_response(status=500, message="文本优化请求失败，请稍后再试。", data=None)

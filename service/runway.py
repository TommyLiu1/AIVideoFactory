import time
from typing import Optional
from config import config
from models.ImageToVideoRequest import ImageToVideoRequest
from models.TextToImageRequest import TextToImageRequest
from utils import utils
from fastapi import  Header
import httpx
from loguru import logger


async def get_runwayml_headers(authorization: Optional[str] = None):
    """获取RunwayML API请求头"""
    auth_token = authorization.split(" ")[1] if authorization else config.runway_default_auth_token
    heads = utils.generate_headers()
    heads.update(
        {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    )
    return heads

async def submit_generate_image_task( request: TextToImageRequest, team_id: int,
        authorization: str = Header(None, description="Runway授权令牌")):
    headers = await get_runwayml_headers(authorization)
    options = request.options.model_dump() if request.options else {}
    width, height = (720, 1280) if request.ratio.find("9:16") != -1 else (1088, 1920)
    seed = int(time.time())
    module = config.image_default_model if not request.model else request.model
    options.update({
        "text_prompt": request.prompt,
        "num_images": request.num,
        "width": width,
        "publicImageGeneratorName": module,
        "seed": seed,
        "diversity": 2,
        "exploreMode": True,
        "flip": True,
        "name": f"{module.replace('-', '')} {request.prompt} a-2, {seed}",
        "assetGroupId": str(utils.get_uuid()),
        "height": height
    })

    payload = {
        "taskType": "text_to_image",
        "internal": False,
        "options": options,
        "asTeamId": team_id,
        "sessionId": request.sessionId or str(utils.get_uuid())
    }
    logger.info(f'[submit_generate_image_task]submit generate image task to runway payload:{payload}'"")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            response = await client.post(config.runway_task_api_url, json=payload, headers=headers)
            result_dict = response.json()
            logger.info(f'[submit_generate_image_task]submit generate image task to runway response:{result_dict}')
            if response.status_code != 200:
                return response.status_code, result_dict.get('error')

            if type(result_dict) is dict:
                return 200, result_dict.get('task').get('id')

    except httpx.HTTPStatusError as e:
        logger.error(f'[submit_generate_image_task] submit generate image task to runway request exception:{e.response.text}')
        return e.response.status_code, e.response.text

    except Exception as e:
        logger.error(f'[submit_generate_image_task] submit generate image task to runway request exception:{e}')
        return 500, str(e)


async def submit_generate_video_task(request: ImageToVideoRequest, team_id: int,
        authorization: str = Header(None, description="Runway授权令牌")):
    headers = await get_runwayml_headers(authorization)
    options = request.options.model_dump() if request.options else {}
    width, height = (768, 1280) if request.ratio.find("9:16") != -1 else (1080, 1920)
    seed = int(time.time())
    model = config.video_default_model if not request.model else request.model
    model_alias = config.video_default_model_alias
    keyframes = []
    keyframes.append({'image':request.image_url, 'timestamp':0})
    options.update({
        "name": f"{model_alias}  {seed}",
        "seconds": request.seconds,
        "width": width,
        "height": height,
        "watermark": False,
        "seed": seed,
        "route": "i2v",
        "text_prompt": request.prompt,
        "exploreMode": True,
        "keyframes": keyframes,
        "assetGroupId": str(utils.get_uuid())
    })

    payload = {
        "taskType": model,
        "internal": False,
        "options": options,
        "asTeamId":team_id,
        "sessionId": request.sessionId or str(utils.get_uuid())
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30)) as client:
            response = await client.post(config.runway_task_api_url, json=payload, headers=headers)
            result_dict = response.json()
            logger.info(f'[submit_generate_video_task] submit generate video task to runway response:{result_dict}')
            if response.status_code != 200:
                return response.status_code, result_dict.get('error')

            if type(result_dict) is dict:
                return 200, result_dict.get('task').get('id')

    except httpx.HTTPStatusError as e:
        logger.error(f'[submit_generate_video_task] submit generate video task to runway request exception:{e.response.text}')
        return e.response.status_code, e.response.text

    except Exception as e:
        logger.error(f'[submit_generate_video_task] submit generate video task to runway request exception:{e}')
        return 500, str(e)


async def verify_profile(authorization: str = Header(None, description="Runway授权令牌")) -> (int,str):
    headers = await get_runwayml_headers(authorization)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            response = await client.get(config.runway_profile_api_url, headers=headers)
            result_dict = response.json()
            logger.info(f'[verify_profile] get profile response:{result_dict}')
            if response.status_code != 200:
                return response.status_code, result_dict.get('error')
            if type(result_dict) is dict:
                return 200, result_dict.get('user').get('id')
    except httpx.HTTPStatusError as e:
        logger.error(f'get profile request exception:{e.response.text}')
        return e.response.status_code, e.response.text
    except Exception as e:
        logger.error(f'get profile request exception:{e}')
        return 500, str(e)

async def estimate_feature_cost_credits(team_id: int, authorization: str = Header(None, description="Runway授权令牌"), model_name: str = 'gen3a_turbo'):
    headers = await get_runwayml_headers(authorization)
    payload = {
        "feature": model_name,
        "count": 1,
        "options": {},
        "asTeamId":team_id
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            response = await client.post(config.runway_estimate_api_url, json=payload, headers=headers)
            result_dict = response.json()
            logger.info(f'[estimate_feature_cost_credits]estimate response:{result_dict}')
            if response.status_code != 200:
                return response.status_code, result_dict.get('error')
            if type(result_dict) is dict:
                return 200, result_dict.get('canUseExploreMode')

    except httpx.HTTPStatusError as e:
        logger.error(f'estimate request exception:{e.response.text}')
        return e.response.status_code, e.response.text
    except Exception as e:
        logger.error(f'estimate request exception:{e}')
        return 500, str(e)


async def query_task(task_id: str, team_id: int, authorization: str = Header(None, description="Runway授权令牌")):
    try:
        headers = await get_runwayml_headers(authorization)
        params = {
            "asTeamId": team_id
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            response = await client.get(
                f"{config.runway_task_api_url}/{task_id}",
                headers=headers,
                params=params
            )
            result_dict = response.json()
            video_or_image_urls = []
            logger.info(f'[query_task]query task response:{result_dict}')
            if response.status_code != 200:
                return response.status_code, video_or_image_urls
            if type(result_dict) is dict:
                status = result_dict.get('task').get('status')
                if status == 'SUCCEEDED':
                    artifacts =  result_dict.get('task').get('artifacts')
                    for artifact in artifacts:
                        video_or_image_urls.append(artifact.get('url'))

                return 200, status, video_or_image_urls

    except httpx.HTTPStatusError as e:
        logger.error(f'[query_task] query task request exception:{e.response.text}')
        return e.response.status_code, e.response.text, []
    except Exception as e:
        logger.error(f'[query_task] query task request exception:{e}')
        return 500, str(e), []




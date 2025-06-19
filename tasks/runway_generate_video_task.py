import asyncio
import random
import json
from fastapi import Header
from loguru import logger

import utils.utils
from models.ImageToVideoRequest import ImageToVideoRequest
from models.TextToImageRequest import TextToImageRequest
from service.db.video_task_db_service import VideoTaskDBService
from utils import utils

from service.runway import (
    submit_generate_image_task,
    query_task as query_runway_task, # Renamed to avoid potential conflicts
    estimate_feature_cost_credits,
    submit_generate_video_task
)
from exceptions.runway_exceptions import RunwayCreditException, RunwayTaskFailedException, RunwayTokenExpiredException



async def _poll_task_status(task_id: str, team_id: int, authorization: str, task_type: str) -> str:
    """Helper function to poll task status and return the artifact URL."""
    while True:
        status_code, status, artifact_urls = await query_runway_task(
            task_id=task_id,
            team_id=team_id,
            authorization=authorization
        )

        logger.info(f"Polling {task_type} task {task_id}: status_code={status_code}, status='{status}', urls={artifact_urls}")

        if status_code != 200:
            error_message = status if isinstance(status, str) else f"Error querying {task_type} task status."
            logger.error(f"{task_type} task {task_id} query failed with status {status_code}: {error_message}")
            if status_code == 401:
                raise RunwayTokenExpiredException(error_message)
            raise RunwayTaskFailedException(f"{task_type} task {task_id} query failed: {error_message}")

        if status == "SUCCEEDED":
            if artifact_urls and len(artifact_urls) > 0:
                logger.info(f"{task_type} task {task_id} succeeded. URL: {artifact_urls}")
                return artifact_urls
            else:
                logger.error(f"{task_type} task {task_id} succeeded but no artifact URL found.")
                raise RunwayTaskFailedException(f"{task_type} task {task_id} succeeded but no artifact URL found.")
        elif status in ["FAILED", "CANCELLED"]:
            logger.error(f"{task_type} task {task_id} {status.lower()}.")
            raise RunwayTaskFailedException(f"{task_type} task {task_id} {status.lower()}.")
        
        await asyncio.sleep(5)


async def _poll_can_submit_image_or_video_task_status(team_id: int, authorization: str, model_name: str = None):
    while True:
        credit_status_code, can_submit_video_or_error = await estimate_feature_cost_credits(
            team_id=team_id,
            authorization=authorization,
            model_name=model_name or 'gen3a_turbo'  # Use model from request or default
        )
        if credit_status_code != 200:
            logger.error(
                f"Failed to estimate credits. Status: {credit_status_code}, Error: {can_submit_video_or_error}")
            if credit_status_code == 401:
                raise RunwayTokenExpiredException(can_submit_video_or_error)
            raise RunwayCreditException(f"Failed to estimate credits: {can_submit_video_or_error}")

        can_submit_video = can_submit_video_or_error
        logger.info(f"Credit estimation result: can_submit_video={can_submit_video}")
        if can_submit_video:
            break
        await asyncio.sleep(5)

    return True


async def generate_video_task(request: ImageToVideoRequest, user_id: int, team_id: int,
                                authorization: str = Header(None, description="Runway授权令牌"), task_id: str = None):
    logger.info(f"Starting video generation task for team_id: {team_id}, request: {json.dumps(request)}")
    update_result = VideoTaskDBService.update_video_task_execution(
        task_id=task_id,
        prompt=request.get('prompt'),
        model=request.get('model'),
        ratio=request.get('ratio'),
        video_duration=request.get('video_duration'),
        video_nums=request.get('video_nums'),
        task_status='started',
    )
    if not update_result:
        logger.warning(f"Failed to update video task execution status to 'started' for task_id: {task_id}")

    image_url_for_videos = request.get('image_url').split(',') if 'image_url' in request else []
    # Step 1-3: Generate image if no image_url is provided
    if len(image_url_for_videos) == 0:
        logger.info("No image_url provided, proceeding to generate image first.")
        if not request.get('prompt'):
            logger.error("Image generation requested (no image_url) but no prompt provided in ImageToVideoRequest.")
            raise ValueError("A prompt is required in ImageToVideoRequest if image_url is not provided, to generate the initial image.")

        text_to_image_req = TextToImageRequest(
            prompt=request.get('prompt'), # Use prompt from ImageToVideoRequest for image generation
            ratio=request.get('ratio'),   # Use ratio from ImageToVideoRequest
            num=int(request.get('video_nums')),   # Generate images, 4 is max
            model='Gen-4',        # Or specify a default image model from config if needed
            asTeamId=team_id,
            sessionId=utils.get_uuid()
        )
        await _poll_can_submit_image_or_video_task_status(team_id, authorization)
        logger.info(f"Submitting image generation task with payload: {text_to_image_req.model_dump()}")
        # Introduce a random delay to avoid hitting API rate limits
        await asyncio.sleep(random.uniform(1, 3))
        img_status_code, img_task_id_or_error = await submit_generate_image_task(
            request=text_to_image_req,
            team_id=team_id,
            authorization=authorization
        )

        if img_status_code != 200:
            logger.error(f"Failed to submit image generation task. Status: {img_status_code}, Error: {img_task_id_or_error}")
            if img_status_code == 401:
                raise RunwayTokenExpiredException(img_task_id_or_error)
            raise RunwayTaskFailedException(f"Failed to submit image generation task: {img_task_id_or_error}")
        
        image_task_id = img_task_id_or_error
        logger.info(f"Image generation task submitted successfully. Task ID: {image_task_id}")

        image_url_for_videos = await _poll_task_status(image_task_id, team_id, authorization, "Image")
    else:
        logger.info(f"Using provided image_url for video generation: {image_url_for_videos}")

    final_videos_urls = []
    for image_url in image_url_for_videos:
        # Step 4: Estimate feature cost credits
        can_submit_video = await _poll_can_submit_image_or_video_task_status(team_id, authorization)
        # Step 5: Submit video generation task if credits are sufficient
        if can_submit_video:
            image_to_video_request = ImageToVideoRequest(
                prompt=request.get('prompt'),
                model=request.get('model', 'Gen-3A-Turbo'),  # Default to Gen-3A-Turbo if not specified
                ratio=request.get('ratio', '9:16'),  # Default to 16:9 if not specified
                seconds=request.get('video_duration', 10),  # Default to 10 seconds if not specified
                numbers=request.get('video_nums', 1),  # Default to 1 video if not specified
                image_url=image_url,
                asTeamId=team_id,
                sessionId=utils.get_uuid()
            )
            logger.info(
                f"Submitting video generation task with payload: {image_to_video_request.model_dump()}")
            await asyncio.sleep(random.uniform(1, 3))
            video_status_code, video_task_id_or_error = await submit_generate_video_task(
                request=image_to_video_request,
                team_id=team_id,
                authorization=authorization
            )

            if video_status_code != 200:
                logger.error(
                    f"Failed to submit video generation task. Status: {video_status_code}, Error: {video_task_id_or_error}")
                if video_status_code == 401:
                    raise RunwayTokenExpiredException(video_task_id_or_error)
                raise RunwayTaskFailedException(f"Failed to submit video generation task: {video_task_id_or_error}")

            video_task_id = video_task_id_or_error
            logger.info(f"Video generation task submitted successfully. Task ID: {video_task_id}")

            # Step 6-7: Poll for video generation status
            final_video_url = await _poll_task_status(video_task_id, team_id, authorization, "Video")
            logger.info(f"Video generation successful. Final video URL: {final_video_url}")
            final_videos_urls.append(final_video_url)

    return final_videos_urls










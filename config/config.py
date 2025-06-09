import shutil
import toml
import os
from loguru import logger

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
config_file = f"{root_dir}/config.toml"

def load_config():
    if os.path.isdir(config_file):
        shutil.rmtree(config_file)

    if not os.path.isfile(config_file):
        example_file = f"{root_dir}/config.example.toml"
        if os.path.isfile(example_file):
            shutil.copyfile(example_file, config_file)
            logger.info("copy config.example.toml to config.toml")

    logger.info(f"load config from file: {config_file}")

    try:
        _config_ = toml.load(config_file)
    except Exception as e:
        logger.warning(f"load config failed: {str(e)}, try to load as utf-8-sig")
        with open(config_file, mode="r", encoding="utf-8-sig") as fp:
            _cfg_content = fp.read()
            _config_ = toml.loads(_cfg_content)
    return _config_

_cfg = load_config()
log_level = _cfg.get("log_level", "DEBUG")
listen_host = _cfg.get("listen_host", "0.0.0.0")
listen_port = _cfg.get("listen_port", 8090)
app_name = _cfg.get("app_name", "")
app_desc = _cfg.get("app_desc", "")
app_version = _cfg.get("app_version", "")
runway_task_api_url = _cfg.get("runway_task_api_url", "")
runway_profile_api_url =  _cfg.get("runway_profile_url", "")
runway_estimate_api_url =  _cfg.get("runway_estimate_url", "")
runway_team_id = _cfg.get("runway_team_id", "")
runway_default_auth_token =  _cfg.get("runway_default_auth_token", "")
video_default_model = _cfg.get("runway_video_model", "")
video_default_model_alias = _cfg.get("runway_video_model_alias", "")
image_default_model = _cfg.get("runway_image_model", "")
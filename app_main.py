import multiprocessing
import platform
import threading

import wx
from loguru import logger
from ui.login_frame import LoginFrame
from ui.main_frame import MainFrame
from utils.sqlite_manager import SQLAlchemyManager
import logging
import os
import subprocess
from config import config
import psutil
import sys

from work import monitor

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")
config_path = os.path.join(base_path, "config.toml")
redis_dir = os.path.join(base_path, "redis")
log_dir = os.path.join(base_path, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_path = os.path.join(log_dir, "server.log")

def start_win_redis_server():
    redis_pid = os.path.join(os.path.dirname(__file__), 'redis', 'redis_6379.pid')
    if os.path.exists(redis_pid):
        os.remove(redis_pid)
    start_bat = os.path.join(os.path.dirname(__file__), 'redis', 'start.bat')
    subprocess.Popen(start_bat, cwd=os.path.dirname(start_bat), shell=True)
    psutil.Process()

def check_process_exist(process_name):
    try:
        procs = list(psutil.process_iter())
        for proc in procs:
            if proc.name() == process_name:
                return True
    except Exception as e:
        logger.error(f"检查进程失败: {e}")
    return False

class MyApp(wx.App):
    def OnInit(self):

        try:
            self.db_manager = SQLAlchemyManager()
            login_frame = LoginFrame(None, title="用户登录")
            login_frame.Show()
            # main_frame = MainFrame(None, title="赚钱视频生成器")
            # main_frame.Show()
            return True
        except Exception as e:
            logging.error(f"启动失败: {e}")
            return False

    def OnExit(self):
        # Ensure the database connection is closed when the app exits
        return 0

if __name__ == '__main__':
    threading.Thread(
        target=monitor.monitor_jobs,
        name="monitor_rq_jobs",
        daemon=True
    ).start()
    app = MyApp()
    app.MainLoop()
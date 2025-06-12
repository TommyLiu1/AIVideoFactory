import multiprocessing
import platform
import wx
from loguru import logger
from ui.login_frame import LoginFrame
from ui.main_frame import MainFrame
from utils.sqlite_manager import SQLAlchemyManager
from work.rq_works import start_simple_rq_worker, start_rq_worker_pool
import logging
import os
import subprocess
from config import config
import psutil

def start_win_redis_server():
    redis_pid = os.path.join(os.path.dirname(__file__), 'redis', 'redis_6379.pid')
    if os.path.exists(redis_pid):
        os.remove(redis_pid)
    start_bat = os.path.join(os.path.dirname(__file__), 'redis', 'start.bat')
    subprocess.Popen(start_bat, cwd=os.path.dirname(start_bat), shell=True)
    psutil.Process()

def check_process_exist(process_name):
    procs = list(psutil.process_iter())
    for proc in procs:
        if proc.name() == process_name:
            return True
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
    os_name = platform.system()
    if os_name == 'Windows':
        # 启动Redis服务器
        if not check_process_exist('redis-server.exe'):
            logger.info("Redis server is not running, begin to start it.")
            multiprocessing.Process(target=start_win_redis_server, daemon=True).start()
        else:
            logger.info("Redis server is already running.")
        # 启动RQ worker
        multiprocessing.Process(target=start_simple_rq_worker, daemon=True).start()
    else:
        # 启动RQ worker
        multiprocessing.Process(target=start_rq_worker_pool, daemon=True).start()

    app = MyApp()
    app.MainLoop()
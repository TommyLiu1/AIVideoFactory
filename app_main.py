import wx
from ui.login_frame import LoginFrame
from ui.main_frame import MainFrame
from utils.sqlite_manager import SQLAlchemyManager
import logging
class MyApp(wx.App):
    def OnInit(self):

        try:
            self.db_manager = SQLAlchemyManager()
            # login_frame = LoginFrame(None, title="用户登录")
            # login_frame.Show()
            main_frame = MainFrame(None, title="赚钱视频生成器")
            main_frame.Show()
            return True
        except Exception as e:
            logging.error(f"启动失败: {e}")
            return False

    def OnExit(self):
        # Ensure the database connection is closed when the app exits
        return 0

if __name__ == '__main__':
    app = MyApp()
    app.MainLoop()
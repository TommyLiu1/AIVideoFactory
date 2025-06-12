import wx
import wx.grid as gridlib

from controllers.v1.VideoGenerateController import generate_video_for_client
from models.ImageToVideoRequest import ImageToVideoRequest
from service.db.user_db_service import UserDBService
from ui.add_task_dialog import AddTaskDialog
import threading
import time

# Import SQLAlchemy components and Task model
from utils.sqlite_manager import SQLAlchemyManager  # Rename Task to avoid conflict with local Task class
from models.db.video_task_excutions import VideoTaskExecution as DBTask
from service.db.video_task_db_service import VideoTaskDBService

# --- Custom Styling Colors (Element UI inspired) ---
ELEM_PRIMARY = wx.Colour(64, 158, 255)  # Element UI default blue
ELEM_SUCCESS = wx.Colour(103, 194, 58)  # Green
ELEM_DANGER = wx.Colour(245, 108, 108)  # Red
ELEM_INFO = wx.Colour(144, 147, 153)  # Grey
ELEM_WARNING = wx.Colour(230, 162, 60)  # Orange

# Text colors for buttons
WHITE_TEXT = wx.WHITE

# ListCtrl colors
LIST_ROW_HOVER_BG = wx.Colour(235, 245, 255)  # Light blue on hover (subtle)
LIST_ROW_SELECTED_BG = wx.Colour(217, 236, 255)  # Slightly darker blue on selection


class MainFrame(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=wx.Size(1280, 700))  # 修正Size类型
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.WHITE)
        self.db_manager = SQLAlchemyManager()
        self.create_widgets()
        self.Centre()
        self.SetMinSize(wx.Size(850, 600))
        # 绑定Grid右键菜单事件
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.grid.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self.on_grid_cell_right_click)
        self.grid.Bind(gridlib.EVT_GRID_SELECT_CELL, self.on_grid_select_cell)
        # Bind activate event to refresh task list when window is activated
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        # Load initial tasks
        self.refresh_task_list()
        self.create_menu_bar()

    def on_size(self, event):
        self.Layout()
        # 重新设置列宽
        total_width = self.panel.GetClientSize().GetWidth() or 1280
        col_ratios = [0.05, 0.18, 0.38, 0.08, 0.13, 0.07, 0.06, 0.05]  # 各列宽度比例，和为1
        for idx, ratio in enumerate(col_ratios):
            self.grid.SetColSize(idx, int(total_width * ratio))
        event.Skip()

    def create_widgets(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        top_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        BTN_HEIGHT = 40

        # Add '新增任务' button
        add_task_button = wx.Button(self.panel, label="新增任务", size=wx.Size(-1, BTN_HEIGHT))
        add_task_button.SetBackgroundColour(wx.BLUE)  # 深灰色背景
        add_task_button.SetForegroundColour(wx.WHITE)
        add_task_button.Bind(wx.EVT_BUTTON, self.on_add_task)
        top_button_sizer.Add(add_task_button, 0, wx.ALL, 5)

        # Add '全选' button
        select_all_button = wx.Button(self.panel, label="全选", size=wx.Size(-1, BTN_HEIGHT))
        select_all_button.SetBackgroundColour(wx.Colour(144, 147, 153)) # 灰色
        select_all_button.SetForegroundColour(wx.WHITE)
        select_all_button.Bind(wx.EVT_BUTTON, self.on_select_all)
        top_button_sizer.Add(select_all_button, 0, wx.ALL, 5)

        # Add '批量运行' button
        batch_run_button = wx.Button(self.panel, label="批量运行", size=wx.Size(-1, BTN_HEIGHT))
        batch_run_button.SetBackgroundColour(wx.Colour(64, 158, 255)) # 蓝色
        batch_run_button.SetForegroundColour(wx.WHITE)
        batch_run_button.Bind(wx.EVT_BUTTON, self.on_batch_run)
        top_button_sizer.Add(batch_run_button, 0, wx.ALL, 5)

        # Add '批量删除' button
        batch_delete_button = wx.Button(self.panel, label="批量删除", size=wx.Size(-1, BTN_HEIGHT))
        batch_delete_button.SetBackgroundColour(wx.RED)
        batch_delete_button.SetForegroundColour(wx.WHITE)
        batch_delete_button.Bind(wx.EVT_BUTTON, self.on_batch_delete)
        top_button_sizer.Add(batch_delete_button, 0, wx.ALL, 5)

        # Add '批量取消' button
        batch_cancel_button = wx.Button(self.panel, label="批量取消", size=wx.Size(-1, BTN_HEIGHT))
        batch_cancel_button.SetBackgroundColour(wx.Colour(230, 162, 60))  # 橙色
        batch_cancel_button.SetForegroundColour(wx.WHITE)
        batch_cancel_button.Bind(wx.EVT_BUTTON, self.on_batch_cancel)
        top_button_sizer.Add(batch_cancel_button, 0, wx.ALL, 5)

        # Add '批量重试' button
        batch_retry_button = wx.Button(self.panel, label="批量重试", size=wx.Size(-1, BTN_HEIGHT))
        batch_retry_button.SetBackgroundColour(wx.Colour(157, 89, 255))   # 紫色
        batch_retry_button.SetForegroundColour(wx.WHITE)
        batch_retry_button.Bind(wx.EVT_BUTTON, self.on_batch_retry)
        top_button_sizer.Add(batch_retry_button, 0, wx.ALL, 5)
        top_button_sizer.AddStretchSpacer(1)
        main_sizer.Add(top_button_sizer, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 5)

        self.grid = gridlib.Grid(self.panel)
        self.grid.CreateGrid(0, 8)  # Create 8 columns initially
        col_labels = ["选择", "任务ID", "提示词", "比例", "模型名称", "时长(秒)", "生成数量", "状态"]
        for idx, label in enumerate(col_labels):
            self.grid.SetColLabelValue(idx, label)
            self.grid.SetColSize(idx, [50, 70, 300, 80, 150, 90, 90, 120][idx])

        # 只需设置为布尔类型即可，去掉自定义渲染器和编辑器
        self.grid.SetColFormatBool(0)
        # 正确方式：为checkbox列设置GridCellAttr并指定renderer/editor
        bool_attr = wx.grid.GridCellAttr()
        bool_attr.SetRenderer(wx.grid.GridCellBoolRenderer())
        bool_attr.SetEditor(wx.grid.GridCellBoolEditor())
        self.grid.SetColAttr(0, bool_attr)
        # 设置除第一列外其它列为只读
        for col in range(1, self.grid.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetReadOnly(True)
            self.grid.SetColAttr(col, attr)

        # Enable editing for the grid
        self.grid.EnableEditing(True)
        # 让Grid表格自适应窗口大小
        main_sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 10)

        # 分页控件
        pagination_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.prev_btn = wx.Button(self.panel, label="上一页")
        self.next_btn = wx.Button(self.panel, label="下一页")
        self.page_label = wx.StaticText(self.panel, label="第 1/1 页")
        self.prev_btn.Bind(wx.EVT_BUTTON, self.on_prev_page)
        self.next_btn.Bind(wx.EVT_BUTTON, self.on_next_page)
        pagination_sizer.Add(self.prev_btn, 0, wx.ALL, 5)
        pagination_sizer.Add(self.next_btn, 0, wx.ALL, 5)
        pagination_sizer.Add(self.page_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        main_sizer.Add(pagination_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(main_sizer)

        # 分页参数
        self.current_page = 1
        self.page_size = 10
        self.total_pages = 1
        self.total_tasks = 0

        # 设置提示词列支持自动换行
        prompt_col = 1
        for row in range(self.grid.GetNumberRows()):
            attr = self.grid.GetOrCreateCellAttr(row, prompt_col)
            attr.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            attr.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            attr.SetOverflow(False)  # 禁止溢出
            attr.SetReadOnly(True)
            attr.SetRenderer(wx.grid.GridCellAutoWrapStringRenderer())
            self.grid.SetAttr(row, prompt_col, attr)


    def create_styled_button(self, label, bg_color, fg_color, handler):
        """Helper to create Element UI styled buttons."""
        btn = wx.Button(self.panel, label=label, size=wx.Size(-1, 40))
        btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        btn.SetBackgroundColour(bg_color)
        btn.SetForegroundColour(fg_color)
        btn.Bind(wx.EVT_BUTTON, handler)
        btn.original_bg_color = bg_color
        btn.Bind(wx.EVT_ENTER_WINDOW, self.on_button_hover)
        btn.Bind(wx.EVT_LEAVE_WINDOW, self.on_button_leave)
        return btn

    def on_button_hover(self, event):
        button = event.GetEventObject()
        original = button.original_bg_color
        hover_color = wx.Colour(min(original.Red() + 20, 255),
                                min(original.Green() + 20, 255),
                                min(original.Blue() + 20, 255))
        button.SetBackgroundColour(hover_color)
        button.Refresh()

    def on_button_leave(self, event):
        button = event.GetEventObject()
        button.SetBackgroundColour(button.original_bg_color)
        button.Refresh()

    def get_task_by_row(self, row):
        if row != -1 and self.grid.GetNumberRows() > row:
            task_id_str = self.grid.GetCellValue(row, 1)  # 任务ID在第1列
            try:
                task = VideoTaskDBService.get_task_by_id(task_id_str)
                return task
            except Exception:
                return None
        return None

    def get_selected_task(self):
        # 兼容旧代码，依然保留
        selected_row = self.grid.GetGridCursorRow()
        return self.get_task_by_row(selected_row)

    def on_grid_select_cell(self, event):
        row = event.GetRow()
        col_count = self.grid.GetNumberCols()
        # 清除之前所有行的高亮
        for r in range(self.grid.GetNumberRows()):
            for c in range(col_count):
                self.grid.SetCellBackgroundColour(r, c, wx.WHITE)
        # 高亮当前选中行
        for c in range(col_count):
            self.grid.SetCellBackgroundColour(row, c, wx.Colour(224, 224, 224))
        self.grid.Refresh()

    def on_grid_cell_right_click(self, event):
        row = event.GetRow()
        self.grid.SelectRow(row)  # 选中右键的行

        # 获取当前行的任务状态
        task, session = self.get_selected_task()
        if not task:
            return
        status = task.task_status
        # 运行中状态不弹出菜单
        if status in ("started", "运行中"):
            return
        menu = wx.Menu()
        font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        if status in ("pending", "待运行"):
            menu_run = menu.Append(wx.ID_ANY, "运行任务")
            menu.AppendSeparator()
            menu_edit = menu.Append(wx.ID_ANY, "编辑任务")
            menu.AppendSeparator()
            menu_delete = menu.Append(wx.ID_ANY, "删除任务")
            self.Bind(wx.EVT_MENU, self.on_run_task, menu_run)
            self.Bind(wx.EVT_MENU, self.on_edit_task, menu_edit)
            self.Bind(wx.EVT_MENU, self.on_delete_task, menu_delete)
            menu_run.SetFont(font)
            menu_edit.SetFont(font)
            menu_delete.SetFont(font)
        elif status in ("failed", "失败"):
            menu_retry = menu.Append(wx.ID_ANY, "重试任务")
            menu.AppendSeparator()
            menu_detail = menu.Append(wx.ID_ANY, "失败详情")
            self.Bind(wx.EVT_MENU, self.on_retry_task, menu_retry)
            self.Bind(wx.EVT_MENU, self.on_view_task, menu_detail)
            menu_retry.SetFont(font)
            menu_detail.SetFont(font)
        elif status in ("finished", "已完成"):
            menu_download = menu.Append(wx.ID_ANY, "下载结果")
            menu.AppendSeparator()
            menu_delete = menu.Append(wx.ID_ANY, "删除任务")
            self.Bind(wx.EVT_MENU, self.on_download_task, menu_download)
            self.Bind(wx.EVT_MENU, self.on_delete_task, menu_delete)
            menu_download.SetFont(font)
            menu_delete.SetFont(font)
        else:
            return  # 其它状态不弹出菜单
        self.PopupMenu(menu)
        menu.Destroy()

    def create_menu_bar(self):
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        # 使用带有快捷键的label格式："菜单项名称\tCtrl+N"
        new_task_item = file_menu.Append(wx.ID_NEW, "新建任务\tCtrl+N")
        file_menu.AppendSeparator()
        settings_item = file_menu.Append(wx.ID_PREFERENCES, "设置\tCtrl+S")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "退出\tCtrl+Q")
        menu_bar.Append(file_menu, "菜单(&M)")
        self.Bind(wx.EVT_MENU, self.on_new_task, new_task_item)
        self.Bind(wx.EVT_MENU, self.on_settings, settings_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.SetMenuBar(menu_bar)
        font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        for item in [new_task_item, settings_item, exit_item]:
            item.SetFont(font)
        # 额外手动绑定加速键（防止部分平台不生效）
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('N'), new_task_item.GetId()),
            (wx.ACCEL_CTRL, ord('S'), settings_item.GetId()),
            (wx.ACCEL_CTRL, ord('Q'), exit_item.GetId()),
        ])
        self.SetAcceleratorTable(accel_tbl)

    def on_settings(self, event):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_exit(self, event):
        dlg = wx.MessageDialog(self, "确定要退出并返回登录界面吗？", "确认退出", wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Hide()
            from ui.login_frame import LoginFrame
            login_frame = LoginFrame(None, title="登录")
            login_frame.Show()
            self.Destroy()
        else:
            dlg.Destroy()

    def on_add_task(self, event):
        dlg = AddTaskDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.refresh_task_list()
        dlg.Destroy()

    def on_new_task(self, event):
        self.on_add_task(event)

    def refresh_task_list(self):
        try:
            self.grid.ClearGrid()
            all_tasks = VideoTaskDBService.query_all_task()
            self.total_tasks = len(all_tasks)
            self.total_pages = max(1, (self.total_tasks + self.page_size - 1) // self.page_size)
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages
            if self.current_page < 1:
                self.current_page = 1
            start = (self.current_page - 1) * self.page_size
            end = start + self.page_size
            tasks = all_tasks[start:end]
            self.page_label.SetLabel(f"第 {self.current_page}/{self.total_pages} 页")
            cur_rows = self.grid.GetNumberRows()
            if cur_rows < len(tasks):
                self.grid.AppendRows(len(tasks) - cur_rows)
            elif cur_rows > len(tasks):
                self.grid.DeleteRows(numRows=cur_rows - len(tasks))
            for i, task in enumerate(tasks):
                self.grid.SetRowSize(i, 45)
                # 初始化复选框状态
                #self.grid.SetCellValue(i, 0, '0')  # 使用'0'字符串，兼容wxGridCellBoolEditor
                self.grid.SetCellValue(i, 1, str(task.get('task_id','')))
                self.grid.SetCellValue(i, 2, str(task.get('prompt', '')))
                self.grid.SetCellValue(i, 3, str(task.get('ratio', '')))
                self.grid.SetCellValue(i, 4, str(task.get('model', '')))
                self.grid.SetCellValue(i, 5, str(task.get('video_duration', '')))
                self.grid.SetCellValue(i, 6, str(task.get('video_nums', '')))
                self.grid.SetCellValue(i, 7, str(task.get('task_status', '')))
                # 设置交替背景色��文字居中（不加粗），只对0~7列设置attr
                for c in range(self.grid.GetNumberCols()-1):
                    if i % 2 == 0:
                        self.grid.SetCellBackgroundColour(i, c, wx.Colour(250, 250, 250))  # 浅灰
                    else:
                        self.grid.SetCellBackgroundColour(i, c, wx.Colour(235, 245, 255))  # 浅蓝
                    attr = wx.grid.GridCellAttr()
                    attr.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
                    attr.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                    self.grid.SetAttr(i, c, attr)

        except Exception as e:
            wx.MessageBox(f"加载任务列表失败: {e}", "数据库错误", wx.OK | wx.ICON_ERROR)

        return True

    def on_run_task(self, event):
        task, session = self.get_selected_task()
        if not task:
            wx.MessageBox("请选择要运行的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        status = task.task_status
        if status.lower() in ["started", "queued", "finished", "failed"]:
            wx.MessageBox("请选择待运行的任务运行", "警告", wx.OK | wx.ICON_WARNING, self)
            return
        VideoTaskDBService.update_task_status(task.task_id, "pending")
        # todo: 启动后台线程运行任务

    def simulate_task_run(self, task_id):
        session = self.db_manager.get_session()
        try:
            task = session.query(DBTask).filter_by(id=task_id).first()
            if not task:
                print(f"Task with ID {task_id} not found in simulate_task_run.")
                return
            duration_in_seconds = getattr(task, 'duration', 1)
            for i in range(duration_in_seconds):
                time.sleep(1)
            if task.id % 2 == 0:
                task.status = "已完成"
                wx.CallAfter(lambda: wx.MessageBox(f"任务 {task.id} 已完成！", "任务完成", wx.OK | wx.ICON_INFORMATION, self))
            else:
                task.status = "失败"
                wx.CallAfter(lambda: wx.MessageBox(f"任务 {task.id} 失败！", "任务失败", wx.OK | wx.ICON_ERROR, self))
            session.commit()
            wx.CallAfter(self.refresh_task_list)
        except Exception as e:
            session.rollback()
            wx.CallAfter(lambda: wx.MessageBox(f"后台任务更新失败: {e}", "数据库错误", wx.OK | wx.ICON_ERROR, self))
        finally:
            session.close()

    def on_edit_task(self, event):
        task_to_edit, session = self.get_selected_task()
        if not task_to_edit:
            wx.MessageBox("请选择要编辑的任务", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        status = task_to_edit.task_status
        if status.lower() in ["started", "queued" ,"finished","failed"]:
            wx.MessageBox("待运行的任务才能允许编辑。", "警告", wx.OK | wx.ICON_WARNING, self)
            return
        dlg = AddTaskDialog(self, task_to_edit)
        if dlg.ShowModal() == wx.ID_OK:
            updated_data = dlg.get_task_data()
            if updated_data:
                task, session = VideoTaskDBService.get_task_by_id(task_to_edit.task_id)
                try:
                    if task:
                        task.prompt = updated_data["prompt"]
                        task.ratio = updated_data["ratio"]
                        task.model_name = updated_data["model"]
                        task.duration = updated_data["count"]
                        task_status = getattr(task, 'task_status', getattr(task, 'status', None))
                        if task_status in ["已完成", "失败"]:
                            if hasattr(task, 'task_status'):
                                task.task_status = "待运行"
                            elif hasattr(task, 'status'):
                                task.status = "待运行"
                        session.commit()
                        self.refresh_task_list()
                except Exception as e:
                    session.rollback()
                    wx.MessageBox(f"任务���辑失败: {e}", "数据库错误", wx.OK | wx.ICON_ERROR, self)
                finally:
                    session.close()
        dlg.Destroy()

    def on_delete_task(self, event):
        task_to_delete, session = self.get_selected_task()
        if not task_to_delete:
            wx.MessageBox("请选择要删除的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        status = task_to_delete.task_status
        if status.lower() in ["started", "queued"]:
            wx.MessageBox("排队中或者运行中的任务，不允许删除。", "警告", wx.OK | wx.ICON_WARNING, self)
            return
        confirm = wx.MessageBox(f"确定要删除任务ID: {task_to_delete.task_id} 吗？", "确认删除", wx.YES_NO | wx.ICON_QUESTION, self)
        if confirm == wx.YES:
            success, msg = VideoTaskDBService.delete_task_by_id(task_to_delete.task_id)
            if success:
                self.refresh_task_list()
            else:
                wx.MessageBox(f"任务删除失败: {msg}", "数据库错误", wx.OK | wx.ICON_ERROR, self)

    def on_view_task(self, event):
        task = self.get_selected_task()
        if not task:
            wx.MessageBox("请选择要查看的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        details = (f"任务ID: {getattr(task, 'id', '')}\n"
                   f"Prompt: {getattr(task, 'prompt', '')}\n"
                   f"Ratio: {getattr(task, 'ratio', '')}\n"
                   f"模型名称: {getattr(task, 'model', '')}\n"
                   f"时长: {getattr(task, 'duration', '')} 秒\n"
                   f"生成数量: {getattr(task, 'generated_count', '')}\n"
                   f"状态: {getattr(task, 'status', '')}")
        wx.MessageBox(details, f"任务详情 - ID: {getattr(task, 'id', '')}", wx.OK | wx.ICON_INFORMATION, self)

    def on_download_task(self, event):
        task = self.get_selected_task()
        if not task:
            wx.MessageBox("请选择要下载的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        if getattr(task, 'status', None) == "已完成":
            wx.MessageBox(f"下载任务 {getattr(task, 'id', '')} 的结果...", "下载", wx.OK | wx.ICON_INFORMATION, self)
        else:
            wx.MessageBox("只有已完成的任务才能下载。", "提示", wx.OK | wx.ICON_WARNING, self)

    def on_cancel_task(self, event):
        task = self.get_selected_task()
        if not task:
            wx.MessageBox("请选择要取消的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        if getattr(task, 'task_status', getattr(task, 'status', '')) in ("started", "运行中"):
            session = self.db_manager.get_session()
            try:
                task_db = session.query(DBTask).filter_by(id=task.id).first()
                if task_db:
                    task_db.task_status = "cancelled"
                    session.commit()
                    wx.MessageBox("任务已取消。", "提示", wx.OK | wx.ICON_INFORMATION, self)
                    self.refresh_task_list()
            except Exception as e:
                session.rollback()
                wx.MessageBox(f"取消任务失败: {e}", "数据库错误", wx.OK | wx.ICON_ERROR, self)
            finally:
                session.close()
        else:
            wx.MessageBox("只有运行中的任务才能取消。", "提示", wx.OK | wx.ICON_WARNING, self)

    def on_retry_task(self, event):
        task = self.get_selected_task()
        if not task:
            wx.MessageBox("请选择要重试的任务。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        if getattr(task, 'task_status', getattr(task, 'status', '')) in ("failed", "失败"):
            session = self.db_manager.get_session()
            try:
                task_db = session.query(DBTask).filter_by(id=task.id).first()
                if task_db:
                    task_db.task_status = "pending"
                    session.commit()
                    wx.MessageBox("任务已重试，状态已重置为待运行。", "提示", wx.OK | wx.ICON_INFORMATION, self)
                    self.refresh_task_list()
            except Exception as e:
                session.rollback()
                wx.MessageBox(f"重试任务失败: {e}", "数据库错误", wx.OK | wx.ICON_ERROR, self)
            finally:
                session.close()
        else:
            wx.MessageBox("只有失败的任务才能重试。", "提示", wx.OK | wx.ICON_WARNING, self)

    # def on_action_cell_click(self, event):
    #     row = event.GetRow()
    #     col = event.GetCol()
    #     if col != 8:
    #         event.Skip()
    #         return
    #     renderer = self.grid.GetCellRenderer(row, col)
    #     if not isinstance(renderer, ActionButtonRenderer):
    #         event.Skip()
    #         return
    #     mouse_pos = event.GetPosition()
    #     rect = self.grid.CellToRect(row, col)
    #     rel_x = mouse_pos.x
    #     rel_y = mouse_pos.y
    #     # 重新计算按钮rect，确保与Draw一致（相对单元格左上角）
    #     btn_width = renderer.btn_width
    #     btn_height = renderer.btn_height
    #     btn_gap = renderer.btn_gap
    #     x = 10
    #     y = (rect.height - btn_height) // 2
    #     for idx, label in enumerate(renderer.btn_labels):
    #         btn_rect = wx.Rect(x, y, btn_width, btn_height)
    #         if btn_rect.Contains(rel_x, rel_y):
    #             if label == "运行":
    #                 self.on_run_task(event)
    #             elif label == "编辑":
    #                 self.on_edit_task(event)
    #             elif label == "删除":
    #                 self.on_delete_task(event)
    #             elif label == "取消":
    #                 self.on_cancel_task(event)
    #             elif label == "重试":
    #                 self.on_retry_task(event)
    #             elif label == "下载":
    #                 self.on_download_task(event)
    #             elif label == "失败详情":
    #                 self.on_view_task(event)
    #             return
    #         x += btn_width + btn_gap
    #     event.Skip()

    def on_prev_page(self, event):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_task_list()

    def on_next_page(self, event):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_task_list()

    def on_activate(self, event):
        if event.GetActive():
            self.refresh_task_list()
        event.Skip()

    def on_select_all(self, event):
        """全选/取消全选切换"""
        btn = event.GetEventObject()
        is_all_selected = all(self.grid.GetCellValue(row, 0) in (True, '1', 1) for row in range(self.grid.GetNumberRows()))
        if is_all_selected:
            for row in range(self.grid.GetNumberRows()):
                self.grid.SetCellValue(row, 0, '')  # 取消全选，必须用空字符串
            btn.SetLabel("全选")
        else:
            for row in range(self.grid.GetNumberRows()):
                self.grid.SetCellValue(row, 0, '1')  # 全选，必须用'1'
            btn.SetLabel("取消全选")

    def on_batch_run(self, event):
        """批量运行任务，只运行状态为pending/待运行的任务"""
        selected_task_ids = []
        for row in range(self.grid.GetNumberRows()):
            if self.grid.GetCellValue(row, 0) == '1':
                status = self.grid.GetCellValue(row, 7)
                if status in ("pending", "待运行"):
                    task_id = self.grid.GetCellValue(row, 1)
                    selected_task_ids.append(task_id)
        if not selected_task_ids:
            wx.MessageBox("请选择状态为待运行的任务进行批量运行。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        for task_id in selected_task_ids:
            self.run_task_by_id(task_id)

    def on_batch_delete(self, event):
        """批量删除任务，支持状态为pending, failed, finished的任务"""
        deletable_task_ids = []
        for row in range(self.grid.GetNumberRows()):
            if self.grid.GetCellValue(row, 0) in (True, '1', 1):
                status = self.grid.GetCellValue(row, 7)
                if status in ("pending", "待运行", "failed", "失败", "finished", "已完成"):
                    task_id = self.grid.GetCellValue(row, 1)
                    deletable_task_ids.append(task_id)
        if not deletable_task_ids:
            wx.MessageBox("请选择可删除（待运行/失败/已完成）的任务。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        confirm = wx.MessageBox(f"确定要批量删除选中的{len(deletable_task_ids)}个任务吗？", "批量删除确认", wx.YES_NO | wx.ICON_QUESTION, self)
        if confirm == wx.YES:
            for task_id in deletable_task_ids:
                VideoTaskDBService.delete_task_by_id(task_id)
            self.refresh_task_list()

    def on_batch_cancel(self, event):
        """批量取消任务，只取消排队中的任务"""
        cancelable_task_ids = []
        for row in range(self.grid.GetNumberRows()):
            if self.grid.GetCellValue(row, 0) in (True, '1', 1):
                status = self.grid.GetCellValue(row, 7)
                if status in ("queued", "排队中"):
                    task_id = self.grid.GetCellValue(row, 1)
                    cancelable_task_ids.append(task_id)
        if not cancelable_task_ids:
            wx.MessageBox("请选择状态为运行中的任务进行批量取消。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        confirm = wx.MessageBox(f"确定要批量取消选中的{len(cancelable_task_ids)}个任务吗？", "批量取消确认", wx.YES_NO | wx.ICON_QUESTION, self)
        if confirm == wx.YES:
            # todo: 实现批量取消逻辑
            self.refresh_task_list()

    def on_batch_retry(self, event):
        """批量重试任务，只重试状态为失败的任务"""
        retryable_task_ids = []
        for row in range(self.grid.GetNumberRows()):
            if self.grid.GetCellValue(row, 0) in (True, '1', 1):
                status = self.grid.GetCellValue(row, 7)
                if status in ("failed", "失败"):
                    task_id = self.grid.GetCellValue(row, 1)
                    retryable_task_ids.append(task_id)
        if not retryable_task_ids:
            wx.MessageBox("请选择状态为失败的任务进行批量重试。", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        confirm = wx.MessageBox(f"确定要批量重试选中的{len(retryable_task_ids)}个任务吗？", "批量重试确认", wx.YES_NO | wx.ICON_QUESTION, self)
        if confirm == wx.YES:
            # todo: 实现批量重试逻辑
            self.refresh_task_list()

    def run_task_by_id(self, task_id):
        """Run a single task by its ID."""
        try:
            # 先更新数据库任务状态为排队中
            success, task = VideoTaskDBService.update_task_status(task_id, "queued", "")
            if not success:
                wx.MessageBox(f"运行任务：{task_id} 失败", "错误", wx.OK | wx.ICON_ERROR)
                return
            request = ImageToVideoRequest(
                prompt=task.prompt,
                ratio=task.ratio,
                model=task.model_name,
                seconds=task.video_duration,
                numbers=task.video_nums,
            )
            user = UserDBService.get_user()
            submit_success, submit_result = generate_video_for_client(request, user.token, task_id)
            if not submit_success:
                if submit_result.find("UnauthorizedError") != -1:
                    wx.MessageBox(f"token已失效，请到设置页面重新更新token", "提示", wx.OK | wx.ICON_ERROR)
                    return
                wx.MessageBox(f"任务 {task_id} 提交失败: {submit_result}", "错误", wx.OK | wx.ICON_ERROR)
                return

        except Exception as e:
            wx.MessageBox(f"运行任务 {task_id} 失败: {e}", "错误", wx.OK | wx.ICON_ERROR)

    def on_grid_cell_changed(self, event):
        # 不要在此事件里再SetCellValue，否则会递归和状态错乱，直接跳过即可
        event.Skip()









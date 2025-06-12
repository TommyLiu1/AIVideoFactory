import wx

class AddTaskDialog(wx.Dialog):
    def __init__(self, parent, existing_task=None):
        super().__init__(parent, title="新增/编辑任务", size=wx.Size(540, 460))
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour("#FFFFFF"))  # 设置面板背景颜色
        self.existing_task = existing_task
        self.task_data = {}
        self.create_widgets()
        self.CentreOnParent()

        if self.existing_task:
            self.load_existing_task_data()

    def create_widgets(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.GridBagSizer(5, 5)

        # Prompt
        prompt_label = wx.StaticText(self.panel, label="任务Prompt:")
        prompt_label.SetForegroundColour(wx.Colour("#000000"))  # 设置字体颜色
        grid_sizer.Add(prompt_label, pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.prompt_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE, size=wx.Size(350, 100))
        self.prompt_text.SetBackgroundColour(wx.Colour("#F7F7F7"))  # Light Gray
        grid_sizer.Add(self.prompt_text, pos=(0, 1), span=(1, 2), flag=wx.EXPAND | wx.ALL, border=5)

        # Optimize Button
        optimize_btn = wx.Button(self.panel, label="提示词优化", size=wx.Size(120, 30))
        optimize_btn.SetBackgroundColour(wx.Colour("#007ACC"))  # 蓝色
        optimize_btn.SetForegroundColour(wx.Colour("#FFFFFF"))  # 白色
        grid_sizer.Add(optimize_btn, pos=(1, 2), flag=wx.ALIGN_RIGHT  | wx.ALL, border=5)

        # Ratio
        ratio_label = wx.StaticText(self.panel, label="Ratio:")
        grid_sizer.Add(ratio_label, pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.ratio_choice = wx.Choice(self.panel, choices=["9:16", "16:9"], size=wx.Size(200, -1))
        grid_sizer.Add(self.ratio_choice, pos=(2, 1), flag=wx.EXPAND | wx.ALL, border=5)

        # Model Name
        model_label = wx.StaticText(self.panel, label="模型名称:")
        grid_sizer.Add(model_label, pos=(3, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.model_choice = wx.Choice(self.panel, choices=["gen3a_turbo"], size=wx.Size(200, -1))
        grid_sizer.Add(self.model_choice, pos=(3, 1), flag=wx.EXPAND | wx.ALL, border=5)

        # Duration
        duration_label = wx.StaticText(self.panel, label="时长(秒):")
        grid_sizer.Add(duration_label, pos=(4, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.duration_choice = wx.Choice(self.panel, choices=["5", "10"], size=wx.Size(200, -1))
        grid_sizer.Add(self.duration_choice, pos=(4, 1), flag=wx.EXPAND | wx.ALL, border=5)

        # Video Nums
        nums_label = wx.StaticText(self.panel, label="生成数量:")
        grid_sizer.Add(nums_label, pos=(5, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        self.nums_choice = wx.Choice(self.panel, choices=[str(i) for i in range(1, 5)], size=wx.Size(200, -1))
        self.nums_choice.SetSelection(0)
        grid_sizer.Add(self.nums_choice, pos=(5, 1), flag=wx.EXPAND | wx.ALL, border=5)

        # 是否运行 Checkbox
        self.run_checkbox = wx.CheckBox(self.panel, label="添加后立即运行")
        self.run_checkbox.SetValue(True)
        grid_sizer.Add(self.run_checkbox, pos=(6, 0), flag=wx.ALIGN_LEFT | wx.ALL, border=5)

        # OK and Cancel buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.panel, wx.ID_OK, label="确定", size=wx.Size(80, 40))
        ok_btn.SetBackgroundColour(wx.Colour(40, 167, 69))  # 绿色
        ok_btn.SetForegroundColour(wx.Colour(255, 255, 255))   # 白色
        cancel_btn = wx.Button(self.panel, wx.ID_CANCEL, label="取消", size=wx.Size(80, 40))
        cancel_btn.SetBackgroundColour(wx.Colour(255, 59, 48))  # 红色
        cancel_btn.SetForegroundColour(wx.Colour(255, 255, 255))   # 白色
        btn_sizer.Add(ok_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        btn_sizer.Add(cancel_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        grid_sizer.Add(btn_sizer, pos=(6, 1), span=(1, 2), flag=wx.ALIGN_CENTER | wx.TOP, border=20)

        main_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 10)
        self.panel.SetSizer(main_sizer)

        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)

    def load_existing_task_data(self):
        if self.existing_task:
            self.prompt_text.SetValue(self.existing_task.prompt)
            self.ratio_choice.SetStringSelection(self.existing_task.ratio)
            self.model_choice.SetStringSelection(self.existing_task.model)
            self.duration_choice.SetStringSelection(str(self.existing_task.video_duration))
            self.nums_choice.SetStringSelection(str(self.existing_task.video_nums))
            # 其他字段加载

    def on_ok(self, event):
        from service.db.video_task_db_service import VideoTaskDBService
        prompt = self.prompt_text.GetValue()
        ratio = self.ratio_choice.GetStringSelection()
        model = self.model_choice.GetStringSelection()
        duration = int(self.duration_choice.GetStringSelection())
        video_nums = int(self.nums_choice.GetStringSelection())
        run_after_add = self.run_checkbox.GetValue()
        success, err = VideoTaskDBService.add_task(prompt, model, ratio, duration, video_nums, run_after_add)
        if success:
            wx.MessageBox('任务已提交！', '成功', wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox(f'任务提交失败: {err}', '错误', wx.OK | wx.ICON_ERROR)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def get_task_data(self):
        return self.task_data

    def EndModal(self, retCode):
        super().EndModal(retCode)
        if retCode == wx.ID_OK:
            parent = self.GetParent()
            if hasattr(parent, 'refresh_task_list'):
                parent.refresh_task_list()

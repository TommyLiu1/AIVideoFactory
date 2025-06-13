import wx
from openai import OpenAI
from config.config import DeepSeek_api_model, DeepSeek_api_key, DeepSeek_api_url
from service.db.video_task_db_service import VideoTaskDBService

class AddTaskDialog(wx.Dialog):
    def __init__(self, parent, existing_task=None, task_id=None):
        super().__init__(parent, title="新增/编辑任务", size=wx.Size(540, 460))
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour("#FFFFFF"))  # 设置面板背景颜色
        self.task_id = task_id
        self.task_data = {}
        self.create_widgets()
        self.CentreOnParent()

        if self.task_id:
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
        optimize_btn.Bind(wx.EVT_BUTTON, self.on_optimize_prompt)
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
        if self.task_id:
            from service.db.video_task_db_service import VideoTaskDBService
            task, session = VideoTaskDBService.get_task_by_id(self.task_id)
            if task:
                self.prompt_text.SetValue(getattr(task, 'prompt', ''))
                self.ratio_choice.SetStringSelection(getattr(task, 'ratio', '9:16'))
                self.model_choice.SetStringSelection(getattr(task, 'model', 'gen3a_turbo'))
                self.duration_choice.SetStringSelection(str(getattr(task, 'video_duration', '5')))
                self.nums_choice.SetStringSelection(str(getattr(task, 'video_nums', '1')))
            session.close()

    def on_optimize_prompt(self, event):
        user_prompt = self.prompt_text.GetValue()
        if not user_prompt.strip():
            wx.MessageBox('请输入需要优化的提示词', '提示', wx.OK | wx.ICON_INFORMATION)
            return
        optimization_instruction ="""
            你是一个提示词优化专家，请优化以下用户输入的提示词，使其更清晰、具体，并符合最佳实践。
            优化后的提示词应：
            - 明确目标（如：是生成视频的文案）
            - 包含必要的细节（如：画面内容、风格、受众）
            - 避免模糊表述
            只需返回优化后的提示词，无需额外解释。
            用户提供的提示词：
            """ + user_prompt

        # 显示loading对话框
        loading = wx.BusyInfo("正在优化提示词，请稍候...", parent=self)
        wx.YieldIfNeeded()
        try:
            ai_client = OpenAI(api_key=DeepSeek_api_key, base_url=DeepSeek_api_url)
            response = ai_client.chat.completions.create(
                model=DeepSeek_api_model,
                messages=[
                    {"role": "user", "content": optimization_instruction}
                ]
            )
            optimized_prompt = response.choices[0].message.content
            self.prompt_text.SetValue(optimized_prompt)
        except Exception as e:
            wx.MessageBox(f'优化失败: {e}', '错误', wx.OK | wx.ICON_ERROR)
        finally:
            del loading
            wx.YieldIfNeeded()

    def on_ok(self, event):

        prompt = self.prompt_text.GetValue()
        ratio = self.ratio_choice.GetStringSelection()
        model = self.model_choice.GetStringSelection()
        duration = int(self.duration_choice.GetStringSelection())
        video_nums = int(self.nums_choice.GetStringSelection())
        run_after_add = self.run_checkbox.GetValue()
        parent = self.GetParent()
        if self.task_id:
            # 编辑模式，更新任务
            success, task = VideoTaskDBService.update_task(self.task_id, prompt, model, ratio, duration, video_nums)
            if success:
                wx.MessageBox('任务已更新！', '成功', wx.OK | wx.ICON_INFORMATION)
                if run_after_add and hasattr(parent, 'run_task_by_id'):
                    parent.run_task_by_id(self.task_id)
                self.EndModal(wx.ID_OK)
            else:
                wx.MessageBox(f'任务更新失败', '错误', wx.OK | wx.ICON_ERROR)
        else:
            # 新增模式
            success, task_dict = VideoTaskDBService.add_task(prompt, model, ratio, duration, video_nums)
            if success:
                wx.MessageBox('任务已提交！', '成功', wx.OK | wx.ICON_INFORMATION)
                if run_after_add and hasattr(parent, 'run_task_by_id'):
                    parent.run_task_by_id(task_dict['task_id'])
                self.EndModal(wx.ID_OK)
            else:
                wx.MessageBox(f'任务提交失败', '错误', wx.OK | wx.ICON_ERROR)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def get_task_data(self):
        return self.task_data

    def EndModal(self, retCode):
        super().EndModal(retCode)
        if retCode == wx.ID_OK:
            parent = self.GetParent()
            if hasattr(parent, 'refresh_task_list'):
                parent.refresh_task_list(is_show_loading=False)



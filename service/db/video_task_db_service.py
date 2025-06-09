class VideoTaskDBService:
    @classmethod
    def query_all_task(cls, user_id: int):
        res_tasks = []
        # 查询队列中的job
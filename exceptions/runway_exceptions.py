
class RunwayTokenExpiredException(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field  # 添加额外属性ca

class RunwayCreditException(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field  # 添加额外属性ca


class RunwayTaskFailedException(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field  # 添加额外属性ca


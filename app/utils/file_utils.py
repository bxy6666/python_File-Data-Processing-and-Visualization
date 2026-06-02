"""成员A接口预留：文件上传、格式校验、数据读取与导出。"""


def read_uploaded_file(file):
    raise NotImplementedError("文件读取逻辑由成员A接入")


def export_dataset(export_type):
    raise NotImplementedError("数据导出逻辑由成员A接入")

# AI 修改记录

## 2026-06-02

- 新增 Flask 最小可运行骨架。
- 新增单页前端流程，包含上传、清洗、分析、可视化、导出入口。
- 为成员A/B/C接口返回统一 `NOT_IMPLEMENTED` 占位响应。
- 为成员D可视化接口返回 `DATA_NOT_READY`，等待数据模块接入。
- 新增项目级 `AGENTS.md` 与 `docs/project-context.md`。
- `run.py` 支持 `PORT` 与 `FLASK_DEBUG` 环境变量，并关闭 reloader，方便后台启动验证。
- 未实现成员A/B/C的具体业务逻辑，未引入大型前端框架。

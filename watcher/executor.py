import importlib


class ListenerExecutor:
    """
    Listener 执行器。

    职责：
    1. 根据 listeners.json 提供的 module / class 动态加载 Listener
    2. 实例化 Listener
    3. 调用统一的 handle(page_id) 接口
    4. 返回执行结果

    不负责：
    - 判断 page_id 属于哪个对象
    - 决定使用哪个 Listener
    - 调用 Notion API
    """

    def execute(self, listener_config, page_id):
        module_name = listener_config.get("module")
        class_name = listener_config.get("class")

        if not module_name:
            return {
                "status": "INVALID_LISTENER_CONFIG",
                "reason": "module_missing",
                "page_id": page_id,
            }

        if not class_name:
            return {
                "status": "INVALID_LISTENER_CONFIG",
                "reason": "class_missing",
                "page_id": page_id,
            }

        try:
            module = importlib.import_module(module_name)
            listener_class = getattr(module, class_name)
            listener = listener_class()

            if not hasattr(listener, "handle"):
                return {
                    "status": "INVALID_LISTENER",
                    "reason": "handle_method_missing",
                    "page_id": page_id,
                    "listener": class_name,
                }

            result = listener.handle(page_id)

            return {
                "status": "EXECUTED",
                "page_id": page_id,
                "listener": class_name,
                "result": result,
            }

        except Exception as e:
            return {
                "status": "EXECUTION_ERROR",
                "page_id": page_id,
                "listener": class_name,
                "error_type": type(e).__name__,
                "error": str(e),
            }
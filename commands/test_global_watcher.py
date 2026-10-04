import time

from watcher.global_watcher import GlobalWatcher


INTERVAL = 5


def main():
    watcher = GlobalWatcher()

    print("GlobalWatcher 已启动")
    print(f"轮询间隔：{INTERVAL} 秒")
    print("-" * 60)

    while True:
        try:
            changes = watcher.check()

            new_count = 0
            changed_count = 0

            for item in changes:
                if item["status"] == "NEW":
                    new_count += 1

                    print(
                        f"[NEW] {item['id']} "
                        f"{item['last_edited_time']}"
                    )

                elif item["status"] == "CHANGED":
                    changed_count += 1

                    print(
                        f"[CHANGED] {item['id']} "
                        f"{item['last_edited_time']}"
                    )

            print(
                f"本轮检查：{len(changes)} 个页面 | "
                f"NEW={new_count} | "
                f"CHANGED={changed_count}"
            )

            time.sleep(INTERVAL)

        except KeyboardInterrupt:
            print("\nGlobalWatcher 已停止")
            break

        except Exception as e:
            print(f"[ERROR] {type(e).__name__}: {e}")

            # 即使一次 API 请求失败，也不要让整个服务退出
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
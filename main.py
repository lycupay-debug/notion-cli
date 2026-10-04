from watcher.service import WatcherService


def main():
    service = WatcherService(interval=10)

    try:
        service.run()
    except KeyboardInterrupt:
        print("\n[Main] 收到停止信号")
        service.stop()
    except Exception as e:
        print(
            f"[Main ERROR] "
            f"{type(e).__name__}: {e}"
        )
        raise


if __name__ == "__main__":
    main()
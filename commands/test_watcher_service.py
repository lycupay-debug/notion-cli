from watcher.service import WatcherService


def main():
    service = WatcherService(interval=5)
    service.run()


if __name__ == "__main__":
    main()
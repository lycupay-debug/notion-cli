from watcher.dispatcher import Dispatcher


PAGE_ID = "3eb7613b-20a9-8138-809b-ee3da6edfe84"


def main():
    dispatcher = Dispatcher()

    result = dispatcher.dispatch(PAGE_ID)

    print("=" * 60)
    print("Dispatcher 本地路由测试")
    print("=" * 60)
    print(f"Page ID: {PAGE_ID}")
    print()

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
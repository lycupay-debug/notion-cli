from watcher.identity_service import ObjectIdentityService


def main():
    service = ObjectIdentityService()

    result = service.check_missing()

    print()
    print("=" * 60)
    print("对象归属校验完成")
    print("=" * 60)
    print(f"本次调用 API：{result['checked']} 个")
    print(f"已有归属跳过：{result['skipped']} 个")
    print(f"失败：{result['failed']} 个")


if __name__ == "__main__":
    main()
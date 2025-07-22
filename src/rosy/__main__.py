import asyncio

from rosy.coordinator.__main__ import main as coordinator_main


def main() -> None:
    asyncio.run(coordinator_main())


if __name__ == '__main__':
    main()

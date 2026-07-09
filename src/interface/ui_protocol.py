"""UI 抽象协议。

不同界面形态都应该实现同一个 run 方法。
这样后续扩展 WebUI、GUI 或其他入口时，不需要改动主程序的启动方式。
"""

from abc import ABC, abstractmethod


class AbstractUI(ABC):
    """用户界面抽象基类。"""

    @abstractmethod
    async def run(self) -> None:
        """启动界面主循环。"""

from abc import ABC, abstractmethod


class BaseTool(ABC):

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Execute the tool."""
        raise NotImplementedError
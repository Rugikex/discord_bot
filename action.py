import types


class Action:
    def __init__(self, func: types.FunctionType, is_music_action: bool, **args):
        self._func = func
        self._is_music_action = is_music_action
        self._args = args

    async def execute(self):
        return await self._func(**self._args)

    def is_music_action(self) -> bool:
        return self._is_music_action

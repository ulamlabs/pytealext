from typing import Union

from pyteal import App, Bytes, Concat, Expr, Int, Itob, MaybeValue, TealType
from pyteal.types import require_type


class State:
    """
    Wrapper around state vars.
    """

    def __init__(self, name: Union[str, Expr], type_hint: TealType = TealType.anytype):
        """
        Args:
            name: a key in the global state, if it's a string it will be converted to Bytes
            type_hint: a type which is expected to be stored, will be checked with each put()
        """
        if isinstance(name, str):
            self._name = Bytes(name)
        else:
            self._name = name  # type: Expr
        self.type_hint = type_hint

    def put(self, value: Expr) -> App:
        """
        Store a value in state schema
        """
        raise NotImplementedError

    def get(self) -> App:
        """
        Get a value from a state schema
        """
        raise NotImplementedError

    def add_assign(self, value_to_add: Expr) -> App:
        """
        Replace the stored value with stored_value + value_to_add.
        Equivalent to:
            stored_value += value_to_add
        """
        if not isinstance(value_to_add, Expr):
            raise ValueError("value_to_add must be an instance of Expr or Expr subclass")
        return self.put(self.get() + value_to_add)

    def sub_assign(self, value_to_subtract: Expr) -> App:
        """
        Replace the stored value with stored_value - value_to_subtract.
        Equivalent to:
            stored_value -= value_to_subtract
        """
        if not isinstance(value_to_subtract, Expr):
            raise ValueError("value_to_subtract must be an instance of Expr or Expr subclass")
        return self.put(self.get() - value_to_subtract)


class LocalState(State):
    """
    Wrapper for accessing local state
    """

    def put(self, value: Expr) -> App:
        require_type(value, self.type_hint)
        return App.localPut(Int(0), self._name, value)

    def get(self) -> App:
        return App.localGet(Int(0), self._name)


class GlobalState(State):
    """
    Wrapper for accessing global state
    """

    def put(self, value: Expr) -> App:
        require_type(value, self.type_hint)
        return App.globalPut(self._name, value)

    def get(self) -> App:
        return App.globalGet(self._name)


def get_global_state_ex(foreign_id: int, key: str) -> MaybeValue:
    """
    Wrapper for global state getter.
    External state variables need to be evaluated before use.

    https://pyteal.readthedocs.io/en/stable/state.html#external-global
    """
    return App.globalGetEx(Int(foreign_id), Bytes(key))


class StateArray:
    """
    Wrapper for state access which utilizes multiple slots
    """

    def __init__(self, prefix: Union[str, Expr]):
        """
        Args:
            prefix: a key prefix in the global state, if it's a string it will be converted to Bytes.
            Prefix should be unique to avoid naming conflicts.
        """
        self._prefix = prefix

    def key_at_index(self, index: Union[int, Expr]) -> Expr:
        """
        Get the actual key (bytes) that will be used to access the state information
        """
        if isinstance(index, int):
            if isinstance(self._prefix, str):
                # index: int, prefix: str
                return Bytes(self._prefix.encode("utf-8") + index.to_bytes(8, "big"))
            # index: int, prefix: Expr
            return Concat(self._prefix, Bytes(index.to_bytes(8, "big")))
        else:  # isinstance(index, Expr)
            if isinstance(self._prefix, str):
                # index: Expr, prefix: str
                return Concat(Bytes(self._prefix), Itob(index))
            # index: Expr, prefix: Expr (u64)
            return Concat(self._prefix, Itob(index))

    def __getitem__(self, index: Union[int, Expr]):
        raise NotImplementedError


class LocalStateArray(StateArray):
    """
    Wrapper for local state access which utilizes multiple slots in local state
    """

    def __getitem__(self, index: Union[int, Expr]):
        return LocalState(self.key_at_index(index))


class LocalStateArray2D(StateArray):
    """
    Wrapper for local state access which utilizes multiple slots in local state organized in 2D array
    """

    def __getitem__(self, indices: tuple[Union[int, Expr], Union[int, Expr]]):
        length, width = indices
        return LocalStateArray(self.key_at_index(length))[width]


class GlobalStateArray(StateArray):
    """
    Wrapper for global state access which utilizes multiple slots in global state
    """

    def __getitem__(self, index: Union[int, Expr]):
        return GlobalState(self.key_at_index(index))


class GlobalStateArray2D(StateArray):
    """
    Wrapper for global state access which utilizes multiple slots in global state organized in 2D array
    """

    def __getitem__(self, indices: tuple[Union[int, Expr], Union[int, Expr]]):
        length, width = indices
        return GlobalStateArray(self.key_at_index(length))[width]

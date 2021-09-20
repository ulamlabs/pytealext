from typing import Union
from pyteal import App, MaybeValue, Int, Bytes, Expr, TealType
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
        require_type(value.type_of(), self.type_hint)
        return App.localPut(Int(0), self._name, value)

    def get(self) -> App:
        return App.localGet(Int(0), self._name)


class GlobalState(State):
    """
    Wrapper for accessing global state
    """

    def put(self, value: Expr) -> App:
        require_type(value.type_of(), self.type_hint)
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

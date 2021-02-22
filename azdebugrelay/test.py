
from typing import Callable
def static_init(cls):
    if getattr(cls, "_static_init", None):
        cls._static_init()
    return cls


@static_init
class _TEST(object):
    _init = False

    @classmethod
    def _static_init(cls):
        print(f"Static Init: {cls._init}")
        cls._init = True
        cls._do_more()

    @staticmethod
    def _do_more():
        print("YESSSSS!!!!")

    @staticmethod
    def myfunc():
        print("hello from func")

_TEST.myfunc()
_TEST.myfunc()
_TEST.myfunc()


def thread_proc(func: Callable, *args, **kwargs):
    if kwargs is not None:
        func(args)
    else:
        func(args)


def ff(qqq: int):
    print(qqq)


thread_proc(ff, {"testname": 1}, testname=1)
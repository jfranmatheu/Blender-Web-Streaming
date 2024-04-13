import pprint

from .globals import GLOBALS


def print_debug(*args) -> None:
    """ 💬 Prints some message ONLY in development environment. """
    if GLOBALS.check_in_development():
        print(f'[{GLOBALS.ADDON_MODULE_NAME}]', *args)


def pprint_debug(title: str, d: dict, sort: bool = False) -> None:
    """ 💬 Prints some pretty dictionary ONLY in development environment. """
    if GLOBALS.check_in_development():
        print_debug('\n+++', title, '++++++++++++++++++++++++++++++++')
        pprint.pprint(d, indent=4, sort_dicts=sort)
        print_debug('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')


class CM_PrintDebug:
    """ 💬 Context Manager to prints some messages wrapping
        some code block. ONLY in development environment. """
    def __init__(self, title: str) -> None:
        self.use_debug = GLOBALS.check_in_development()
        if self.use_debug:
            print(f"<{GLOBALS.ADDON_MODULE_NAME}> - {title} ----------------------------------")

    def __enter__(self):
        def print_indent(msg: str, indent: int = 1, prefix: str = '>'):
            if self.use_debug:
                t_char = '\t'
                print(f"{''.join([t_char for i in range(indent)])}{prefix} {msg}")
        return print_indent

    def __exit__(self, exc_type, exc_value, trace):
        if self.use_debug:
            print('</> -----------------------------------------')
            # print(f"</{GLOBALS.ADDON_MODULE_NAME}>")
            # print_debug('----------------------------------------------------------------------------\n')

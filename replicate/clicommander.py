
class UserError(Exception):
    pass

class CLI_Route:
    def __init__(self, name, f):
        self.name = name
        self.f = f

class CLI_Commander:
    def __init__(self):
        self.routes = []
        self.command(self.help)

    def basic_help(self):
        print('enter "help" for basic command list')
        print('enter "exit" or "quit" to close')

    def help(self, cmd, args):
        for x in self.routes:
            print(x.name)

    def command(self, f):
        self.routes.append(CLI_Route(f.__name__, f))

    def execute(self, cmd, args):
        for rt in self.routes:
            if rt.name == cmd:
                rt.f(cmd, args)
                return True
        return False

GLOBAL_ROUTER = None

def init_global_router(embeds):
    global GLOBAL_ROUTER
    CLI_Commander2 = type('CLI_Commander2', (CLI_Commander,), embeds)
    GLOBAL_ROUTER = CLI_Commander2()
    return GLOBAL_ROUTER

def get_global_router(auto=False):
    global GLOBAL_ROUTER
    if GLOBAL_ROUTER == None and auto:
        GLOBAL_ROUTER = CLI_Commander()
    return GLOBAL_ROUTER

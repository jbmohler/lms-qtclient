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
        rtname = self._normalize(f.__name__)
        self.routes.append(CLI_Route(rtname, f))

    @staticmethod
    def _normalize(cmd):
        return cmd.lower().replace("-", "_")

    def matched_routes(self, cmd):
        cmd2 = self._normalize(cmd)
        exact, approx = None, []

        for rt in self.routes:
            if rt.name == cmd2:
                exact = rt
            elif rt.name.startswith(cmd2):
                approx.append((rt, "approx"))

        return exact, approx

    def execute(self, cmd, args):
        exact, approx = self.matched_routes(cmd)

        rt = None
        if exact != None:
            rt = exact
        if exact == None and len(approx) == 1:
            rt = approx[0][0]

        if rt != None:
            rt.f(cmd, args)
            return True
        elif len(approx) > 0:
            lines = ["Candidates:"] + [rt.name for rt, _ in approx]
            print("\n\t".join(lines))
        return False


GLOBAL_ROUTER = None


def init_global_router(embeds):
    global GLOBAL_ROUTER
    CLI_Commander2 = type("CLI_Commander2", (CLI_Commander,), embeds)
    GLOBAL_ROUTER = CLI_Commander2()
    return GLOBAL_ROUTER


def get_global_router(auto=False):
    global GLOBAL_ROUTER
    if GLOBAL_ROUTER == None and auto:
        GLOBAL_ROUTER = CLI_Commander()
    return GLOBAL_ROUTER

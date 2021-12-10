import os
import configparser
import time
import json
import uuid
import datetime
import socket
import urllib.parse
import jose.jwt
import requests
import tzlocal
import rtlib
from . import identity


class RtxError(Exception):
    pass


class RtxRequestCancellation(RtxError):
    pass


class RtxServerError(RtxError):
    pass


def exception_string(request, method):
    if request.status_code == 401:
        return f"The request to {request.url} is not authorized."
    return """\
Server request failed with status code:  {0.status_code}
URL:  {0.url}
Method:  {1}""".format(
        request, method
    )


def raise_exception_ex(request, method):
    if request.status_code in (400, 403):
        t = request.text
        is_json = len(t) > 0 and t[0] == "[" and t[-1] == "]"
        if is_json:
            keys = json.loads(request.text)[0]
            if "error-msg" in keys and keys["error-key"] == "cancel":
                raise RtxRequestCancellation(keys["error-msg"])
            if "error-msg" in keys:
                raise RtxError(keys["error-msg"])
    raise RtxServerError(exception_string(request, method))


class STATIC:
    @staticmethod
    def client_side_items(settings_name, withkey=False):
        # hard coded items!
        raise RuntimeError("check server")


class RtxSession(requests.Session):
    def __init__(self, server_url=None):
        super(RtxSession, self).__init__()
        if server_url:
            self.set_base_url(server_url)
        else:
            self.server_url = None
        self.headers["X-Yenot-Timezone"] = tzlocal.get_localzone().zone

        self.access_token_expiration = None
        self.access_token = None
        self._recent_reports = []

        self.settings_map = {}

    def connected(self):
        return self.server_url is not None

    def authenticated(self):
        return self.access_token is not None

    @property
    def yenot_sid(self):
        token = self.cookies["YenotToken"]
        claims = jose.jwt.get_unverified_claims(token)
        return claims["yenot-session-id"]

    def set_base_url(self, server_url):
        self.server_url = server_url
        if self.server_url and not self.server_url.endswith("/"):
            self.server_url += "/"
        self.mount(self.server_url, requests.adapters.HTTPAdapter(max_retries=3))

    def save_device_token(self):
        client = self.std_client()
        content = client.post(
            "api/user/{}/device-token/new",
            self.rtx_userid,
            device_name=f"{socket.gethostname()} (Desktop client)",
            expdays=int(365.25 * 6),
        )
        saved_token = content.main_table().rows[0].token

        update_auth_config(
            server_url=self.server_url,
            username=self.rtx_username,
            device_token=saved_token,
        )

    def prefix(self, tail):
        return self.server_url + tail

    def static_settings(self, settings_name, withkey=False):
        try:
            return STATIC.client_side_items(settings_name, withkey)
        except RuntimeError:
            pass

        try:
            table = self.settings_map[settings_name]
        except KeyError:
            raise RuntimeError(
                f"call ensure_static_settings with the name {settings_name}"
            )

        return [
            r._as_tuple()[0] if not withkey else r._as_tuple()[:2] for r in table.rows
        ]

    def ensure_static_settings(self, settings_names):
        not_yet_here = set(settings_names).difference(set(self.settings_map.keys()))
        if len(not_yet_here) == 0:
            # already there, all done
            return

        client = self.std_client()
        params = {f"s{i}": v for i, v in enumerate(not_yet_here)}
        content = client.get("api/static_settings", **params)

        for k, table in content.all_tables():
            self.settings_map[k] = table

    def authorized(self, activity):
        for row in self._capabilities.rows:
            if row.act_name == activity:
                return True
        return False

    def authenticate_pin1(self, username, pin):
        p = {"username": username, "pin": pin}
        try:
            r = self.post(self.prefix("api/session-by-pin"), data=p)
        except requests.ConnectionError:
            raise RtxServerError(f"The login server {self.server_url} was unavailable.")
        except requests.Timeout:
            raise RtxServerError(
                f"The login server {self.server_url} was slow responding."
            )
        if r.status_code != 200:
            if r.status_code in (400, 403):
                raise RtxError("Invalid user name or password.  Check your caps lock.")
            else:
                raise raise_exception_ex(r, "POST")

        payload = json.loads(r.text)

        # success, but we are not really authenticated so we do not set
        # access_token or access_token_expiration; counting on a follow-up in
        # authenticate_pin2
        return True

    def authenticate_pin2(self, pin2):
        p = {"pin2": pin2}
        try:
            r = self.post(self.prefix("api/session/promote-2fa"), data=p)
        except requests.ConnectionError:
            raise RtxServerError(f"The login server {self.server_url} was unavailable.")
        except requests.Timeout:
            raise RtxServerError(
                f"The login server {self.server_url} was slow responding."
            )
        if r.status_code != 200:
            if r.status_code in (400, 403):
                raise RtxError("Invalid user name or password.  Check your caps lock.")
            else:
                raise raise_exception_ex(r, "POST")

        payload = json.loads(r.text)

        self.rtx_userid = payload["userid"]
        self.rtx_username = payload["username"]
        self._capabilities = rtlib.ClientTable(*payload["capabilities"])
        self.access_token = True
        self.access_token_expiration = time.time() + 60 * 60
        return True

    def authenticate(self, username, password=None, device_token=None):
        p = {"username": username}
        if password is not None:
            p["password"] = password
        if device_token is not None:
            p["device_token"] = device_token
        try:
            r = self.post(self.prefix("api/session"), data=p)
        except requests.ConnectionError:
            raise RtxServerError(f"The login server {self.server_url} was unavailable.")
        except requests.Timeout:
            raise RtxServerError(
                f"The login server {self.server_url} was slow responding."
            )
        if r.status_code not in (200, 210):
            raise RtxServerError(
                f"Login response failed from server {self.server_url}.\n\n{exception_string(r, 'POST')}"
            )
        elif r.status_code == 210:
            raise RtxError("Invalid user name or password.  Check your caps lock.")

        payload = json.loads(r.text)

        # success
        self.rtx_userid = payload["userid"]
        self.rtx_username = payload["username"]
        self._capabilities = rtlib.ClientTable(*payload["capabilities"])
        self.access_token = True
        self.access_token_expiration = time.time() + 60 * 60
        return True

    def refresh_token(self):
        if not self.access_token_expiration:
            return

        # All the action is in the cookie exchange
        if time.time() + 10 * 60 >= self.access_token_expiration:
            r = self.get(self.prefix("api/session/refresh"))
            if r.status_code in (401, 403):
                # If the refresh token cannot be refreshed try simply starting
                # a new session with the device token.  One reason this could
                # happen is if a transient network failure prevents receiving
                # the response from a prior refresh call and the token is
                # rotated out.
                read_yenotpass(self)
            elif r.status_code != 200:
                raise raise_exception_ex(r, "GET")

    def logout(self):
        if self.access_token:
            r = self.put(self.prefix("api/session/logout"))
            if r.status_code != 200:
                raise raise_exception_ex(r, "PUT")

            # manually clear this
            self.access_token = None
            self.access_token_expiration = None

    def close(self):
        self.logout()

        super(RtxSession, self).close()

    def report_python_traceback_event(self, ltype, descr, data):
        # Save the last logs along with a timestamp so that error reporting is
        # throttled according to the following rules:
        #  1) Never send more than one report per minute
        #  2) Never send the same report (i.e. same call stack frames &
        #     message) more than once every 10 minutes

        now = datetime.datetime.utcnow()
        if (
            len(self._recent_reports) > 0
            and (now - self._recent_reports[0][0]).seconds < 60
        ):
            # enforce rule 1 above
            return

        f = {"data": json.dumps(data).encode("utf8")}
        # Python's hash surely isn't immune to a hash collision where different
        # traceback data structure may hash to the same thing.  The result
        # would be that the second would be dropped.  This possibility is
        # relatively small and the results of not reporting that second
        # (different) error isn't a big deal.
        myhash = hash(f["data"])

        # Purge anything beyond 10 minutes
        n = [
            (tstamp, h)
            for tstamp, h in self._recent_reports
            if (now - tstamp).seconds < 600
        ]
        self._recent_reports = n

        for tstamp, h in self._recent_reports:
            if h == myhash:
                # enforce rule 2 above
                return

        self._recent_reports.insert(0, (now, myhash))

        client = self.std_client()
        try:
            client.post("api/event", logtype=ltype, descr=descr, files=f)
        except:
            pass

    def raw_client(self):
        return RtxClient(self, lambda x: x)

    def std_client(self):
        return RtxClient(self, StdPayload)

    def json_client(self):
        return RtxClient(self, json.loads)


class RequestFuture:
    def __init__(self, session):
        self.session = session
        self.cancel_token = str(uuid.uuid1())
        self.cancelled = False
        self.running = False

    def cancel(self):
        self.cancelled = True
        if self.running and self.cancel_token != None:
            self.session.put(
                self.session.prefix("api/request/cancel"),
                params={"token": self.cancel_token},
            )

    def get(self, client, tail, *args, **kwargs):
        kwargs["cancel_token"] = self.cancel_token
        try:
            self.running = True
            result = client.get(tail, *args, **kwargs)
        finally:
            self.running = False
            self.cancel_token = None
        return result


class RtxClient:
    """
    This class implements the following client-side functionality of the rtx
    server:

    - Rtx server long request 303 waits and retries.
    - Unpacking the body of the response (currently json.loads)

    It does so with-out any GUI toolkit dependency.  Errors and progress
    indications are implemented via exceptions and callbacks.  Background
    threads will be used and managed internally as appropriate (although
    "appropriate" has not been clearly defined nor implemented).

    The star of this class is get which sends a REST request to the specified
    rtx server via the Python requests library.  It notifies the user of errors
    by message box or exception as appropriate and configured by a callback
    (?).  If no error occurs the response is parsed by json.loads and returned
    with-out further parsing.  Note that you should expect requests to
    potentially take a long time.

    TODO:  error callback not yet written ... message boxes for the moment

    :param session:  the as-yet-amorphous connection manager
    """

    def __init__(self, session, result_factory):
        self.session = session
        self.result_factory = result_factory

    def view_help(self, tail):
        os.startfile(self.session.prefix("docs/" + tail))

    def future_invocation(self):
        future = RequestFuture(self.session)
        invoke = lambda *args, **kwargs: future.get(self, *args, **kwargs)
        return future, invoke

    def get(self, tail, *args, **kwargs):
        tail = tail.format(*args)
        s = self.session
        headers = {}
        if "cancel_token" in kwargs:
            headers["X-Yenot-CancelToken"] = kwargs["cancel_token"]
            del kwargs["cancel_token"]
        s.refresh_token()
        r = s.get(s.prefix(tail), params=kwargs, headers=headers, allow_redirects=True)
        # This is special rtx queued long job handling logic
        while r.status_code in [202, 303]:  # accepted, redirect
            queued = r.headers["Location"]
            if "Expected-Duration" in r.headers:
                sleeptime = float(r.headers["Expected-Duration"])
                if sleeptime > 2.0:
                    sleeptime /= 1.5
                time.sleep(sleeptime)
            r = s.get(queued, allow_redirects=True)
        if r.status_code != 200:
            raise raise_exception_ex(r, "GET")
        return self.result_factory(r.text)

    def post(self, tail, *args, **kwargs):
        tail = tail.format(*args)
        if "files" in kwargs:
            files = kwargs.pop("files")
        else:
            files = None
        if "data" in kwargs:
            data = kwargs.pop("data")
        else:
            data = None
        s = self.session
        s.refresh_token()
        r = s.post(
            s.prefix(tail), params=kwargs, data=data, files=files, allow_redirects=True
        )
        # This is special rtx queued long job handling logic
        while r.status_code in [202, 303]:  # accepted, redirect
            queued = r.headers["Location"]
            if "Expected-Duration" in r.headers:
                sleeptime = float(r.headers["Expected-Duration"])
                if sleeptime > 2.0:
                    sleeptime /= 1.5
                time.sleep(sleeptime)
            r = s.get(queued, allow_redirects=True)
        if r.status_code != 200:
            raise raise_exception_ex(r, "POST")
        return self.result_factory(r.text)

    def put(self, tail, *args, **kwargs):
        tail = tail.format(*args)
        if "files" in kwargs:
            files = kwargs.pop("files")
        else:
            files = None
        if "data" in kwargs:
            data = kwargs.pop("data")
        else:
            data = None
        s = self.session
        s.refresh_token()
        r = s.put(
            s.prefix(tail), params=kwargs, data=data, files=files, allow_redirects=True
        )
        # This is special rtx queued long job handling logic
        while r.status_code in [202, 303]:  # accepted, redirect
            queued = r.headers["Location"]
            if "Expected-Duration" in r.headers:
                sleeptime = float(r.headers["Expected-Duration"])
                if sleeptime > 2.0:
                    sleeptime /= 1.5
                time.sleep(sleeptime)
            r = s.get(queued, allow_redirects=True)
        if r.status_code != 200:
            raise raise_exception_ex(r, "PUT")
        return self.result_factory(r.text)

    def delete(self, tail, *args, **kwargs):
        tail = tail.format(*args)
        if "files" in kwargs:
            files = kwargs.pop("files")
        else:
            files = None
        s = self.session
        s.refresh_token()
        r = s.delete(s.prefix(tail), params=kwargs, files=files, allow_redirects=True)
        # This is special rtx queued long job handling logic
        while r.status_code in [202, 303]:  # accepted, redirect
            queued = r.headers["Location"]
            if "Expected-Duration" in r.headers:
                sleeptime = float(r.headers["Expected-Duration"])
                if sleeptime > 2.0:
                    sleeptime /= 1.5
                time.sleep(sleeptime)
            r = s.get(queued, allow_redirects=True)
        if r.status_code != 200:
            raise raise_exception_ex(r, "DELETE")
        return self.result_factory(r.text)


class StdPayload:
    def __init__(self, rawpay):
        self._pay = rawpay
        if isinstance(rawpay, str):
            self._pay = json.loads(rawpay)
        else:
            self._pay = rawpay

    @property
    def keys(self):
        return self._pay

    # def has_named_table(self, name):
    #    if '__main_table__' in self._pay[0] and name == self._pay[0]['__main_table__']:
    #        return True
    #    return name in self._pay[0]

    def all_tables(self):
        for tname in self._pay.keys():
            if self._pay[tname] != None and len(self._pay[tname]) == 2:
                yield tname, self.named_table(tname)

    def named_table(self, name, mixin=None):
        return rtlib.ClientTable(*self._pay[name], mixin=mixin)

    def main_table(self, mixin=None):
        mn = self._pay["__main_table__"]
        return self.named_table(mn, mixin)

    def named_columns(self, name):
        return self._pay[name][0]

    def main_columns(self):
        mn = self._pay["__main_table__"]
        return self.named_columns(mn)


def read_yenotpass(session):
    ypfile = os.path.join(identity.get_appdata_dir(), "config")

    config = configparser.ConfigParser()
    config.read(ypfile)

    if "login" in config.sections():
        login = config["login"]
        session.server_url = login.get("server_url")

        if "username" in login and "password" in login:
            session.authenticate(login["username"], login["password"])

        if "username" in login and "device_token" in login:
            session.authenticate(login["username"], device_token=login["device_token"])


def update_auth_config(**kwargs):
    ypfile = os.path.join(identity.get_appdata_dir(), "config")
    if not os.path.exists(os.path.dirname(ypfile)):
        os.makedirs(os.path.dirname(ypfile), exist_ok=True)

    config = configparser.ConfigParser()
    config.read(ypfile)

    if "login" not in config.sections():
        config.add_section("login")

    login = config["login"]
    for k, v in kwargs.items():
        login[k] = str(v)

    config.write(open(ypfile, "w"))


def auto_session(arg_url=None):
    session = RtxSession()
    try:
        read_yenotpass(session)
    except RtxServerError:
        # we cannot authenticate, that's fine and just like if there was no
        # stored auth at all
        pass
    return session

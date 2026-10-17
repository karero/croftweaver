"""gsc_query.py --no-browser — a scheduled run must never wait for a browser (S9).

Why: track.sh runs from launchd with nobody at the screen. Without the flag, a token
that can't refresh silently sends gsc_query into the OAuth browser flow, and the job
hangs forever — the Bing and AI checks after it never run. With the flag it must exit 2
with instructions, for BOTH ways a token goes bad: no usable token (RuntimeError from
load_credentials) and a refresh Google rejects (RefreshError).

The google libraries are replaced with stubs in sys.modules, so this runs in CI without
them — and each test asserts the saved token was actually loaded, so a missing-library
exit 2 (load_credentials' ImportError branch) can't pass for the right one.

Run:  python3 -m unittest discover -s skills/search-console-insights/scripts/tests
"""
import contextlib
import io
import os
import sys
import tempfile
import types
from pathlib import Path
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import gsc_query  # noqa: E402


class RefreshError(Exception):
    pass


def google_stubs(creds, calls, signed_in=None):
    """Stand-ins for the google modules load_credentials imports. With signed_in, the
    browser flow succeeds and returns it; without, reaching the flow fails the test."""
    class Credentials:
        @staticmethod
        def from_authorized_user_file(path, scopes):
            calls.append("loaded token")
            return creds

    class Flow:
        @staticmethod
        def from_client_secrets_file(*a, **k):
            calls.append("browser flow")
            if signed_in is None:
                raise AssertionError("the browser flow must never start with --no-browser")
            return types.SimpleNamespace(run_local_server=lambda port: signed_in)

    mods = {
        "google": types.ModuleType("google"),
        "google.oauth2": types.ModuleType("google.oauth2"),
        "google.oauth2.credentials": types.ModuleType("google.oauth2.credentials"),
        "google.auth": types.ModuleType("google.auth"),
        "google.auth.transport": types.ModuleType("google.auth.transport"),
        "google.auth.transport.requests": types.ModuleType("google.auth.transport.requests"),
        "google.auth.exceptions": types.ModuleType("google.auth.exceptions"),
        "google_auth_oauthlib": types.ModuleType("google_auth_oauthlib"),
        "google_auth_oauthlib.flow": types.ModuleType("google_auth_oauthlib.flow"),
    }
    mods["google.oauth2.credentials"].Credentials = Credentials
    mods["google.auth.transport.requests"].Request = lambda: None
    mods["google.auth.exceptions"].RefreshError = RefreshError
    mods["google_auth_oauthlib.flow"].InstalledAppFlow = Flow
    return mods


class Creds:
    def __init__(self, valid=False, expired=True, refresh_token=None, refresh_raises=None):
        self.valid, self.expired, self.refresh_token = valid, expired, refresh_token
        self._raises = refresh_raises

    def refresh(self, request):
        if self._raises:
            raise self._raises


class NoBrowser(unittest.TestCase):
    def run_main(self, creds, *extra):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            token = os.path.join(d, "token.json")
            Path(token).write_text("{}")
            secret = os.path.join(d, "client_secret.json")
            Path(secret).write_text("{}")  # present, so only the flag decides whether a browser opens
            argv = ["gsc_query.py", "--site", "sc-domain:example.com", "--token", token,
                    "--client-secret", secret, *extra]
            err = io.StringIO()
            with mock.patch.dict(sys.modules, google_stubs(creds, calls)), \
                    mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(gsc_query, "build_service",
                                      side_effect=AssertionError("must stop before the API")), \
                    contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    gsc_query.main()
        return cm.exception.code, err.getvalue(), calls

    def test_no_refresh_token_exits_2_without_browser(self):
        code, err, calls = self.run_main(Creds(refresh_token=None), "--no-browser")
        self.assertEqual(code, 2)
        self.assertEqual(calls, ["loaded token"])
        self.assertIn("sign-in needs renewing", err)

    def test_rejected_refresh_exits_2(self):
        code, err, calls = self.run_main(
            Creds(refresh_token="r", refresh_raises=RefreshError("invalid_grant")), "--no-browser")
        self.assertEqual(code, 2)
        self.assertEqual(calls, ["loaded token"])
        self.assertIn("RefreshError", err)

    def test_missing_token_file_exits_2_without_browser(self):
        # The one case that used to hang: no token.json at all (a fresh machine, a deleted file).
        calls = []
        with tempfile.TemporaryDirectory() as d:
            secret = os.path.join(d, "client_secret.json")
            Path(secret).write_text("{}")
            argv = ["gsc_query.py", "--site", "sc-domain:example.com", "--token",
                    os.path.join(d, "absent.json"), "--client-secret", secret, "--no-browser"]
            err = io.StringIO()
            with mock.patch.dict(sys.modules, google_stubs(Creds(), calls)), \
                    mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    gsc_query.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(calls, [])  # never reached the browser flow (or loaded a token)
        self.assertIn("sign-in needs renewing", err.getvalue())

    def test_missing_google_libraries_exit_2_with_their_own_message(self):
        # Distinct from a dead sign-in: the owner needs to install, not to reconnect.
        blocked = {m: None for m in ("google.oauth2.credentials", "google.auth.transport.requests",
                                     "google_auth_oauthlib.flow", "google.auth.exceptions")}
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(sys.modules, blocked), \
                mock.patch.object(sys, "argv", ["gsc_query.py", "--site", "sc-domain:example.com",
                                                "--token", os.path.join(d, "t.json"), "--no-browser"]), \
                contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                gsc_query.main()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("Missing dependencies", err.getvalue())

    def test_without_the_flag_the_browser_flow_still_starts(self):
        # Interactive behaviour is unchanged: the owner at a terminal still gets the browser.
        # (The stub raises instead of opening one; reaching it is the point.)
        with self.assertRaises(AssertionError) as cm:
            self.run_main(Creds(refresh_token=None))
        self.assertIn("browser flow must never start", str(cm.exception))


class Reconnect(unittest.TestCase):
    """The owner's way back after a scheduled run exits 2: a run without --no-browser.

    Why: a rejected refresh is how a dead sign-in shows up (revoked, or the 7-day token a
    Google app in Testing gets), and the exit-2 line says to reconnect, which re-runs
    gsc_query without the flag. That run used to call the same refresh, get the same
    refusal and stop on a traceback, so reconnecting never worked until someone deleted
    token.json by hand (BUGLOG 2026-10-14, the weekly job row). It must open the browser
    sign-in instead and save the new token over the dead one."""

    def test_rejected_refresh_opens_the_browser_and_saves_the_new_token(self):
        calls = []
        dead = Creds(refresh_token="r", refresh_raises=RefreshError("invalid_grant"))
        fresh = types.SimpleNamespace(to_json=lambda: '{"token": "new"}')
        with tempfile.TemporaryDirectory() as d:
            token = Path(d, "token.json")
            token.write_text('{"token": "dead"}')
            secret = Path(d, "client_secret.json")
            secret.write_text("{}")
            argv = ["gsc_query.py", "--site", "sc-domain:example.com", "--token", str(token),
                    "--client-secret", str(secret)]
            err = io.StringIO()
            reached = []
            with mock.patch.dict(sys.modules, google_stubs(dead, calls, signed_in=fresh)), \
                    mock.patch.object(sys, "argv", argv), \
                    mock.patch.object(gsc_query, "build_service",
                                      side_effect=lambda c: reached.append(c) or sys.exit(9)), \
                    contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    gsc_query.main()
            saved = token.read_text()
        self.assertEqual(cm.exception.code, 9)  # went on to the API with the new sign-in
        self.assertEqual(calls, ["loaded token", "browser flow"])
        self.assertIs(reached[0], fresh)
        self.assertEqual(saved, '{"token": "new"}')
        self.assertIn("Google refused the saved Search Console sign-in", err.getvalue())

    def test_non_interactive_callers_still_get_the_refusal(self):
        # insights.py and search_report.py call load_credentials(interactive=False) and turn
        # the RefreshError into their own message; the fallback must not reach them.
        calls = []
        with tempfile.TemporaryDirectory() as d:
            token = Path(d, "token.json")
            token.write_text("{}")
            dead = Creds(refresh_token="r", refresh_raises=RefreshError("invalid_grant"))
            with mock.patch.dict(sys.modules, google_stubs(dead, calls)):
                with self.assertRaises(RefreshError):
                    gsc_query.load_credentials(Path(d, "client_secret.json"), token,
                                               interactive=False)
        self.assertEqual(calls, ["loaded token"])


class DefaultClientFile(unittest.TestCase):
    """Without --client-secret, the OAuth client file is read from ~/.config/gsc-insights,
    never from the current folder. Why: run from a site's folder, the old default found a
    client_secret.json there, and the site's .gitignore did not keep it out of a commit."""

    def run_main(self, home_has_secret):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            default = Path(d, "home", ".config", "gsc-insights", "client_secret.json")
            default.parent.mkdir(parents=True)
            if home_has_secret:
                default.write_text("{}")
            site = Path(d, "site")
            site.mkdir()
            (site / "client_secret.json").write_text("{}")  # the file the old default picked up
            argv = ["gsc_query.py", "--site", "sc-domain:example.com",
                    "--token", os.path.join(d, "absent.json")]
            env = {k: v for k, v in os.environ.items() if k != "GSC_CLIENT_SECRET"}
            err = io.StringIO()
            cwd = os.getcwd()
            os.chdir(site)
            try:
                with mock.patch.dict(sys.modules, google_stubs(Creds(), calls)), \
                        mock.patch.dict(os.environ, env, clear=True), \
                        mock.patch.object(gsc_query, "DEFAULT_SECRET", default), \
                        mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(err):
                    try:
                        gsc_query.main()
                        code = None
                    except SystemExit as e:
                        code = e.code
                    except AssertionError:  # the stub flow: reached the browser step
                        code = "flow"
            finally:
                os.chdir(cwd)
            return code, err.getvalue(), calls, str(default)

    def test_a_client_file_in_the_current_folder_is_not_used(self):
        code, err, calls, default = self.run_main(home_has_secret=False)
        self.assertEqual(code, 2)
        self.assertIn(f"OAuth client not found: {default}", err)
        self.assertNotIn("browser flow", calls)

    def test_the_file_in_the_config_folder_is_used(self):
        code, _, calls, _ = self.run_main(home_has_secret=True)
        self.assertEqual(code, "flow")
        self.assertEqual(calls, ["browser flow"])


if __name__ == "__main__":
    unittest.main()

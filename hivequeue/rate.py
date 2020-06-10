"""
Rate limiting submodule for the hivequeue library
==================================
Users of the hivequeue library should only concern themselvees with
the RateLimit class, if at all.

This submodule is meant for use by RpcClient objects and implements simple
rate limiting in the form of delayed asynchonous invocation for its RpcQueue
polling loop.


"""

import asyncio
import time
import datetime
import logging
import email.utils
import numpy as np

def retry_to_seconds(retry):
    """Convert a textual time to a unix time number

    Parameters
    ----------
    retry : str
            Retry or Reset time in string form.

    Returns
    -------
    int or None
            Unix time in seconds or None if parse error.
    """
    timetuple = email.utils.parsedate(retry)
    if timetuple:
        parsed_time = timetuple[:6]
        return int(time.mktime(datetime.datetime(*parsed_time).timetuple()))
    return None

class FakeServer:
    """If the server doesn't actually support draft-polli-ratelimit-headers-00 rate limit
    headers yet, we use a built-in fake server to generate fake headers according to a supplied
    pollicy."""
    # pylint: disable=R0903
    def __init__(self, fallback_window, fallback_count):
        """Constructor

        Parameters
        ----------
        fallback_window : int
                          The window length in seconds.
        fallback_count : int
                         The number of requests allowed per window length seconds.
        """
        self.fallback_window = fallback_window
        self.fallback_count = fallback_count
        if self.fallback_count is None:
            self.fallback_window = None
        if self.fallback_window is not None:
            self.curwindow_end = int(time.time()) + self.fallback_window
            self.curwindow_count = 0
    def __call__(self):
        """Fetch a set of fake headers using the pollicy of the FakeServer.

        Returns
        -------
        dict
                Dict with fake rate limit header values.
        """
        if self.fallback_window is None:
            return {
                "RateLimit-Limit": "1000",
                "RateLimit-Remaining": "999",
                "RateLimit-Reset": "1"
            }
        now = int(time.time())
        if now < self.curwindow_end:
            self.curwindow_count += 1
        else:
            self.curwindow_count = 1
            while time.time() >= self.curwindow_end:
                self.curwindow_end += self.fallback_window
        rval = dict()
        rval["RateLimit-Limit"] = str(self.fallback_count) + \
                                  ", " + str(self.fallback_count) + \
                                  ";window=" + str(self.fallback_window)
        remaining = self.fallback_count - self.curwindow_count
        if remaining < 0:
            rval["RateLimit-Remaining"] = "0"
            rval["Retry-After"] = str(self.curwindow_end - now)
        else:
            rval["RateLimit-Remaining"] = str(remaining)
        rval["RateLimit-Remaining"] = str(self.fallback_count - self.curwindow_count)
        rval["RateLimit-Reset"] = str(self.curwindow_end - now)
        return rval

class BackOff:
    """A little helper class for adding some randomness to backoff times."""
    # pylint: disable=R0903
    def __init__(self, mu=30):
        """Constructor.

        Parameters
        ----------
        mu : int
             Number of seconds to back off 'on average'.
             Sigma will be one fifth of this value.
        """
        self.mean = mu
        self.sigma = mu / 5.0
    def __call__(self):
        """Fetch backoff time.

        Returns
        -------
        float
                Number of seconds to back off
        """
        rval = -1.0
        while rval <= 0.0:
            rval = np.random.normal(self.mean, self.sigma, 1)[0]
        logging.info("Backing off for  %f seconds", rval)
        return rval



# draft-polli-ratelimit-headers-00
class RateLimit:
    # pylint: disable=R0902
    """A rate-limit helper class for the RpcClient objects. A RateLimit object provides a simple
    function invocation delay implementation for allowing RpcClient objects to respect JSON-RPC
    API node rate limiting headers, given that the API node implements
    draft-polli-ratelimit-headers-00 defined headers.

    If the API node does not yet support draft-polli-ratelimit-headers-00, client side rate limiting
    has been implemented and is default set to 10 requests per second in 15 second windows.

    It is possible to disable rate limiting if needed."""
    def __init__(self,
                 funct,
                 loop,
                 polli_spare=0,
                 fallback_window=15,
                 fallback_count=150,
                 back_off_mu=30
                ):
        # pylint: disable=R0913
        """Constructor:

        Parameters
        ----------

        func : function
               The function to invoke; possibly delayed because of rate limmiting.
        loop : asyncio.AbstractEventLoop
        polli_spare : int
                     The number of spare units to leave untouched of the available units
                     in a current time window.
        fallback_window : int
                         If the server doesn't implement rate limiting, the window size to
                         use for client side fallback rate limits.
        fallback_count : int
                        If the server doesn't implement rate limiting, the per window quota
                        to use for client side fallback rate limits.
        back_off_mu : int
                      On server errors, the mean number of seconds to back off. Note that
                      Gaussian randomness (sigma is mu/5) is added to avoid server restore overload.
        """
        self.funct = funct
        self.loop = loop
        self.polli_spare = polli_spare
        self.fakeserver = FakeServer(fallback_window, fallback_count)
        self.backoff = BackOff(back_off_mu)
        self.probed = False
        self.use_fallback = False
        self.behind = 0
        self.policies = []
        self.limit = None
        self.remaining = None
        self.reset = None
        self.retry = False

    def __call__(self, *args, **kwargs):
        """Invoke the wrapped function. If must be delayed to make sure rate limmits
        are not exceeded.
        """
        # New call not yet returned, means we will be one extra behind when invoking
        self.behind += 1
        if not self.probed:
            self.loop.call_soon(self.funct, *args, **kwargs)
        else:
            #Not the first call
            if self.use_fallback:
                # Use fallback if needed
                self.headers(200, self.fakeserver(), fallback=True)
            # If within the rules of the rate limiter, call soon.
            if self.remaining is not None and self.remaining > self.polli_spare:
                self.remaining -= 1
                self.loop.call_soon(self.funct, *args, **kwargs)
            else:
                #If not, wait for the reset moment plus some extra.
                waitfor = self.reset - time.time() + 0.01
                if waitfor <= 0.0:
                    # We can't rait a negative time.
                    self.loop.call_soon(self.funct, *args, **kwargs)
                else:
                    # Wait the amount of time till the reset time.
                    self.loop.call_later(waitfor, self._retry, *args, **kwargs)

    def _retry(self, *args, **kwargs):
        if self.remaining is not None and self.remaining > self.polli_spare:
            self.remaining -= 1
            self.loop.call_soon(self.funct, *args, **kwargs)
        else:
            #If not, wait for the reset moment plus some extra.
            waitfor = self.reset - time.time() + 0.01
            if waitfor <= 0.0:
                # We can't rait a negative time.
                self.loop.call_soon(self.funct, *args, **kwargs)
            else:
                # Wait the amount of time till the reset time.
                self.loop.call_later(waitfor, self._retry, *args, **kwargs)

    def headers(self, status, headers, fallback=False):
        """Process headers, either from the real server, or if that server doesn't
        implement rate limit headers, from the built-in client side fake server.

        Parameters
        ----------
        status : int
                 The HTTP status from the server
        headers : dict
                 Dict with HTTP header key/value pairs
        fallback : bool
                   Boolean indicating if called from __call__ with fake server values.
        """
        if not fallback:
            # One less behind if these are real headers
            self.behind -= 1
        # Process RateLimit headers depending on mode
        if fallback or not self.use_fallback or not self.probed:
            if "RateLimit-Limit" in headers:
                self.limit = int(headers["RateLimit-Limit"].split(",")[0])
            else:
                self.limit = None
            if "RateLimit-Remaining" in headers:
                self.remaining = int(headers["RateLimit-Remaining"]) - self.behind
            else:
                self.limit = None
            if not fallback or not self.retry:
                if "RateLimit-Reset" in headers:
                    self.reset = headers["RateLimit-Reset"]
                    if not self.reset.isdigit():
                        self.reset = retry_to_seconds(self.reset)
                    else:
                        self.reset = float(self.reset) + time.time()
                else:
                    self.reset = None
            if not self.probed:
                self.probed = True
                if self.limit is not None or self.remaining is not None or self.reset is not None:
                    self.use_fallback = False
                else:
                    self.use_fallback = True
        if "Retry-After" in headers:
            self.reset = headers["Retry-After"]
            self.reset = retry_to_seconds(self.reset)
            self.remaining = 0
            self.retry = True
        else:
            self.retry = False
        if status in [500, 502, 503, 504]:
            logging.info('Status: %d.', status)
            self.reset = self.backoff() + time.time()
        elif status in [413]:
            logging.info('Status: 429 too many requests.')
            if self.reset is None:
                self.reset = self.backoff() + time.time()
        if fallback and self.use_fallback and self.reset is None and \
           (self.remaining is None or self.remaining <= self.polli_spare):
            self.reset = self.backoff() + time.time()
        elif (not fallback and
              not self.use_fallback and
              self.reset is None and
              (self.remaining is None or
               self.remaining <= self.polli_spare
              )
             ):
            logging.info('Missing rate limit headers from response headers.')
            self.reset = self.backoff() + time.time()

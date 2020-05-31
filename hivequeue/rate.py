import asyncio
import time
import email.utils

def retry_to_seconds(retry):
    try:
        parsed_time = email.utils.parsedate(retry)[:6]
        return time.mktime(datetime.datetime(*parsed_time).timetuple())
    except:
        return None

class FakeServer:
    def __init__(self, fallback_window, fallback_count):
        self.fallback_window = fallback_window
        self.fallback_count = fallback_count
        if self.fallback_count is None:
            self.fallback_window = None
        if self.fallback_window is not None:    
            self.curwindow_end = int(time.time()) + self.fallback_window
            self.curwindow_count = 0
    def __call__(self):
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


# draft-polli-ratelimit-headers-00
class RateLimit:
    def __init__(self,
                 funct,                 # The function to rate limit
                 loop,                  # The asyncio loop
                 polli_spare=0,         # We may not want to completely exaust the remaining units
                 fallback_window=None,  # If no Polli headers are given on probe, generate fake
                                        #  headers from provided fallback pollicy.
                 fallback_count=None
                ):
        self.funct = funct
        self.loop = loop
        self.polli_spare = polli_spare
        self.fakeserver = FakeServer(fallback_window, fallback_count)
        self.probed = False
        self.use_fallback = False
        self.behind = 0
        self.policies = []
        self.limit = None
        self.remaining = None
        self.reset = None
        self.retry = False

    def __call__(self, *args, **kwargs):
        # Loop untill call soon is called and loop_on set to False
        loop_on = True
        # New call not yet returned, means we will be one extra behind when invoking
        self.behind += 1
        while loop_on:
            #If this is the first call, call directly, need a response with headers before
            # rate limit can commence.
            if not self.probed:
                self.loop.call_soon(self.funct(*args, **kwargs))
                loop_on = False
            else:
                if self.use_fallback:
                    # Use fallback if needed
                    self.headers(200, self.fakeserver(), fallback=True)
                # If within the rules of the rate limiter, call soon.
                if self.remaining and self.remaining > self.polli_spare:
                    self.remaining -= 1
                    self.loop.call_soon(self.funct(*args, **kwargs))
                    loop_on = False
                else:
                    #If not, wait for the reset moment.
                    waitfor = self.reset - time.time()
                    if waitfor <= 0.0:
                        self.loop.call_soon(self.funct(*args, **kwargs))
                        loop_on = False
                    else:
                        asyncio.sleep(waitfor)

    def headers(self, status, headers, fallback=False):
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
                        self.reset += time.time()
                else:
                    self.reset = None
            if not self.probed:
                self.probed = True
                if self.limit is not None or self.remaining is not None or self.reset is not None:
                    self.use_fallback = False
                else:
                    self.use_fallback = True
        if "Retry-After" in headers:
            self.reset = retry_to_seconds(self.reset)
            self.remaining = 0
            self.retry = True
        else:
            self.retry = False

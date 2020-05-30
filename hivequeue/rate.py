import asyncio
import time
import email.utils

def retry_to_seconds(retry):
    try:
        parsed_time = email.utils.parsedate(retry)[:6]
        return time.mktime(datetime.datetime(*parsed_time).timetuple())
    except:
        return None


class LimitNone:
    def __init__(self, funct, loop):
        self.funct = funct
        self.loop = loop

    def __call__(self, *args, **kwargs):
        self.loop.call_soon(self.funct(*args, **kwargs))

    def headers(self, headers):
        pass


class LimitWindow:
    def __init__(self, funct, loop, limit, interval=60):
        self.funct = funct
        self.loop = loop
        self.limit = limit
        self.interval = interval
        self.interval_start = 0
        self.interval_count = 0

    def __call__(self, *args, **kwargs):
        loop_on = True
        while loop_on:
            now = int(time.time())
            if self.interval_start + self.interval < now:
                self.interval_start = now
                self.interval_count = 0
            if self.interval_count < self.limit:
                self.interval_count += 1
                self.loop.call_soon(self.funct(*args, **kwargs))
                loop_on = False
            else:
                time_left = self.interval + self.interval_start - time.time()
                if time_left > 0.0:
                    asyncio.sleep(time_left)
                else:
                    self.interval_count += 1
                    self.loop.call_soon(self.funct(*args, **kwargs))
                    loop_on = False

    def headers(self, headers):
        pass


class LimitCredits:
    def __init__(self, funct, loop, rate, startboost=0, ceiling=100):
        self.funct = funct
        self.loop = loop
        self.rate = rate
        self.credits = startboost
        self.ceiling = ceiling
        self.last_time = time.time()

    def __call__(self, *args, **kwargs):
        loop_on = True
        while loop_on:
            now = time.time()
            self.credits = (now - self.last_time) * self.rate
            if self.credits > self.ceiling:
                self.credits = self.ceiling
            self.last_time = now
            if credits >= 1.0:
                self.credits -= 1.0
                self.loop.call_soon(self.funct(*args, **kwargs))
                loop_on = False
            else:
                credits_needed = 1.0001 - self.credits
                time_to_credit = credits_needed / self.rate
                asyncio.sleep(time_to_credit)

    def headers(self, headers):
        pass


# draft-polli-ratelimit-headers-00
class LimitPolli:
    def __init__(self, funct, loop):
        self.funct = funct
        self.loop = loop
        self.has_headers = False
        self.behind = 0
        self.limit = None
        self.remaining = None
        self.reset = None

    def __call__(self, *args, **kwargs):
        loop_on = True
        self.behind += 1
        while loop_on:
            if not self.has_headers:
                self.loop.call_soon(self.funct(*args, **kwargs))
                loop_on = False
            else:
                if self.remaining and self.remaining > 0:
                    self.remaining -= 1
                    self.loop.call_soon(self.funct(*args, **kwargs))
                    loop_on = False
                else:
                    waitfor = self.reset - time.time()
                    if waitfor <= 0.0:
                        self.loop.call_soon(self.funct(*args, **kwargs))
                        loop_on = False
                    else:
                        asyncio.sleep(waitfor)

    def headers(self, headers):
        self.behind -= 1
        if "RateLimit-Limit" in headers:
            self.limit = int(headers["RateLimit-Limit"].split(",")[0])
        else:
            self.limit = None
        if "RateLimit-Remaining" in headers:
            self.remaining = int(headers["RateLimit-Remaining"]) - self.behind
        else:
            self.limit = None
        if "RateLimit-Reset" in headers:
            self.reset = headers["RateLimit-Reset"]
            if not self.reset.isdigit():
                self.reset = retry_to_seconds(self.reset)
            else:
                self.reset += time.time()
        elif "Retry-After" in headers:
            self.reset = retry_to_seconds(self.reset)
        else:
            self.reset = None
        if not self.has_headers:
            if self.limit is not None:
                self.has_headers = True
            if self.remaining is not None:
                self.has_headers = True
            if self.reset is not None:
                self.has_headers = True
        else:
            something = False
            if self.limit is not None:
                something = True
            if self.remaining is not None:
                something = True
            if self.reset is not None:
                something = True
            if not something:
                self.has_headers = False

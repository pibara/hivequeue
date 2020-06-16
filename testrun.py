#!/usr/bin/python3.8
import asyncio
import time
import hivequeue

class Generator:
    def __init__(self, burst):
        self.count = 0
        self.remaining = burst
        loop = asyncio.get_running_loop()
        self.ratelimit = hivequeue.RateLimit(self, loop, fallback_window=5, fallback_count=50)
        self(0)
    def __call__(self, num):
        self.count += 1
        if self.count > 1:
            self.ratelimit.headers(200, {})
        if self.remaining > 0:
            self.ratelimit(self.count)
            self.remaining -= 1
    def get_counter(self):
        return self.count

async def main():
    start = time.time()
    burst = 200
    generator = Generator(burst)
    counter = generator.get_counter()
    print("D0:", time.time() - start, counter)
    while counter < burst:
        await asyncio.sleep(1)
        newcounter = generator.get_counter()
        newcount = newcounter - counter
        counter = newcounter
        print("D7:", time.time() - start, newcounter, newcount)

asyncio.run(main())


#!/usr/bin/python3.8
import asyncio
import time
import hivequeue

class Counter:
    def __init__(self):
        self.counter = 0
    def __call__(self, num):
        print("  - ", num)
        self.counter += 1
    def get_counter(self):
        return self.counter

async def main():
    start = time.time()
    burst = 1000
    cnt = Counter()
    loop = asyncio.get_running_loop()
    rl = hivequeue.RateLimit(cnt,loop)
    for num in range(0, burst):
        print("D5", time.time())
        rl(num)
        rl.headers(200,{})
    print("D6:", time.time() - start, cnt.get_counter())
    while cnt.get_counter() < burst:
        await asyncio.sleep(1)
        print("D7:", time.time() - start, cnt.get_counter())

asyncio.run(main())


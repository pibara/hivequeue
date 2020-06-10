#!/usr/bin/python3.8
import asyncio
import time
import hivequeue

class Counter:
    def __init__(self):
        self.counter = 0
    def __call__(self, num):
        #print("  - ", num)
        self.counter += 1
    def get_counter(self):
        return self.counter

async def main():
    start = time.time()
    burst = 5000
    cnt = Counter()
    loop = asyncio.get_running_loop()
    rl = hivequeue.RateLimit(cnt, loop, fallback_window=1, fallback_count=5)
    for num in range(0, burst):
        rl(num)
        rl.headers(200,{})
    counter = cnt.get_counter()
    print("D6:", time.time() - start, counter)
    while counter < burst:
        await asyncio.sleep(1)
        newcounter = cnt.get_counter()
        newcount = newcounter - counter
        counter = newcounter
        print("D7:", time.time() - start, cnt.get_counter(), newcount)

asyncio.run(main())


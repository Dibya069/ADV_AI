
import os
import time
import asyncio
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# --------------------------------------------------
# COMMON UTILITIES
# --------------------------------------------------

def log(message):
    print(
        f"[PID: {os.getpid()} | "
        f"TID: {threading.get_ident()}] {message}",
        flush=True
    )


def measure(label, function):
    print(f"\n{'=' * 65}")
    print(f"RUNNING: {label}")
    print("=" * 65)

    start = time.perf_counter()

    function()

    elapsed = time.perf_counter() - start

    print(f"\n{label} completed in {elapsed:.3f} seconds")

    return elapsed


# --------------------------------------------------
# A. I/O-BOUND TASK
# --------------------------------------------------

def io_task(task_id, delay):
    log(f"Task {task_id} STARTED")

    time.sleep(delay)

    log(f"Task {task_id} COMPLETED")


# 1. Sequential I/O
def sequential_io(tasks, delay):
    for task_id in range(tasks):
        io_task(task_id, delay)


# 2. Multithreading I/O
def threaded_io(tasks, delay, workers):

    with ThreadPoolExecutor(max_workers=workers) as executor:

        executor.map(
            lambda task_id: io_task(task_id, delay),
            range(tasks)
        )


# 3. Asyncio I/O
async def async_io_task(task_id, delay):

    log(f"Async Task {task_id} STARTED")

    await asyncio.sleep(delay)

    log(f"Async Task {task_id} COMPLETED")


async def async_io(tasks, delay):

    await asyncio.gather(
        *[
            async_io_task(task_id, delay)
            for task_id in range(tasks)
        ]
    )


# --------------------------------------------------
# B. CPU-BOUND TASK
# --------------------------------------------------

def cpu_task(args):

    task_id, iterations = args

    log(f"CPU Task {task_id} STARTED")

    result = 0

    for i in range(iterations):
        result += (i * 31) % 97

    log(f"CPU Task {task_id} COMPLETED")

    return result


# 1. Sequential CPU execution
def sequential_cpu(tasks, iterations):

    for task_id in range(tasks):
        cpu_task((task_id, iterations))


# 2. Multithreading CPU execution
def threaded_cpu(tasks, iterations, workers):

    task_args = [
        (task_id, iterations)
        for task_id in range(tasks)
    ]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(cpu_task, task_args))


# 3. Multiprocessing CPU execution
def multiprocessing_cpu(tasks, iterations, workers):

    task_args = [
        (task_id, iterations)
        for task_id in range(tasks)
    ]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        list(executor.map(cpu_task, task_args))


# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Concurrency and Parallelism Lab"
    )

    parser.add_argument("--tasks", type=int, default=6)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--io-delay", type=float, default=1.0)
    parser.add_argument("--iterations", type=int, default=1500000)

    args = parser.parse_args()

    tasks = args.tasks
    workers = args.workers
    delay = args.io_delay
    iterations = args.iterations

    if tasks < 1 or workers < 1 or delay < 0 or iterations < 1:
        parser.error("Tasks/workers/iterations must be positive and delay non-negative")

    print("\nCONCURRENCY & PARALLELISM LAB")
    print("-" * 50)

    print(f"CPU cores available : {os.cpu_count()}")
    print(f"Tasks               : {tasks}")
    print(f"Thread/Process pool : {workers}")
    print(f"I/O delay           : {delay}s")
    print(f"CPU iterations      : {iterations:,}")

    results = {}

    # ----------------------------------------------
    # I/O BENCHMARK
    # ----------------------------------------------

    print("\n\n######## I/O-BOUND BENCHMARK ########")

    results["Sequential I/O"] = measure(
        "Sequential I/O",
        lambda: sequential_io(tasks, delay)
    )

    results["Threaded I/O"] = measure(
        "Threaded I/O",
        lambda: threaded_io(tasks, delay, workers)
    )

    results["Asyncio I/O"] = measure(
        "Asyncio I/O",
        lambda: asyncio.run(async_io(tasks, delay))
    )

    # ----------------------------------------------
    # CPU BENCHMARK
    # ----------------------------------------------

    print("\n\n######## CPU-BOUND BENCHMARK ########")

    results["Sequential CPU"] = measure(
        "Sequential CPU",
        lambda: sequential_cpu(tasks, iterations)
    )

    results["Threaded CPU"] = measure(
        "Threaded CPU",
        lambda: threaded_cpu(tasks, iterations, workers)
    )

    results["Multiprocessing CPU"] = measure(
        "Multiprocessing CPU",
        lambda: multiprocessing_cpu(tasks, iterations, workers)
    )

    # ----------------------------------------------
    # FINAL COMPARISON
    # ----------------------------------------------

    print("\n\n######## FINAL RESULTS ########")

    for name, elapsed in results.items():

        baseline = (
            results["Sequential I/O"]
            if "I/O" in name
            else results["Sequential CPU"]
        )

        speedup = baseline / elapsed if elapsed else 0

        print(
            f"{name:25} | "
            f"{elapsed:8.3f}s | "
            f"Speedup: {speedup:.2f}x"
        )


if __name__ == "__main__":
    main()


"""
Run the program:
python3 concurrency_lab.py
or
python3 concurrency_lab.py \
    --tasks 8 \
    --workers 4 \
    --io-delay 1 \
    --iterations 1500000
"""
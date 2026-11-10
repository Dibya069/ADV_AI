# Python Concurrency & Parallelism

### A visual field guide for Python and system-design interviews

> **The one question that decides your execution model:**\
> Is the program mostly **waiting** for something, or mostly
> **computing** something?

------------------------------------------------------------------------

# 1. Start with the big picture

``` mermaid
flowchart TD
    A[Work arrives] --> B{What is the bottleneck?}
    B -->|Waiting: network, DB, disk| C[I/O-bound]
    B -->|Calculating: transforms, loops| D[CPU-bound]
    C --> E{Can the library use async I/O?}
    E -->|Yes| F[asyncio]
    E -->|No| G[Thread pool]
    D --> H{Need parallel CPU execution?}
    H -->|Yes| I[Process pool / worker processes]
    H -->|No, small workload| J[Run normally]
    F --> K[Bound concurrency + timeouts]
    G --> K
    I --> L[Bound workers + queue]
    J --> M[Measure before optimizing]
```

  Workload    Think of it as...                Typical choice
  ----------- -------------------------------- -------------------------
  I/O-bound   Waiting for a restaurant order   `asyncio` or threads
  CPU-bound   Cooking the meal                 Processes / native code
  Mixed       Taking orders while cooking      Async I/O + worker pool

**Important distinction:** the workload determines the tool---not the
fact that the code is written with `async def`.

------------------------------------------------------------------------

# 2. Concurrency vs parallelism --- see the difference

Imagine three tasks, A, B and C. Each takes one second.

## Sequential: finish one, then start the next

``` text
Time →   0s       1s       2s       3s
         |--------|--------|--------|
Task A   [========]
Task B            [========]
Task C                     [========]

Total ≈ 3 seconds
```

## Concurrent: overlap the waiting periods

``` text
Time →   0s       1s
         |--------|
Task A   [ waiting ]
Task B   [ waiting ]
Task C   [ waiting ]

Total ≈ 1 second (for independent 1-second waits)
```

The tasks overlap in time. They do not need to execute instructions at
the exact same instant.

## Parallel: execute on separate CPU cores

``` text
Time →   0s       1s
         |--------|
Core 1   [ Task A ]
Core 2   [ Task B ]
Core 3   [ Task C ]

Total ≈ 1 second (if work can be split and overhead is small)
```

### Keep this mental model

-   **Sequential:** one cashier handles one customer at a time.
-   **Concurrency:** one cashier switches between customers while each
    waits for something.
-   **Parallelism:** multiple cashiers serve customers at the same time.

Concurrency is about **coordination and overlapping progress**.
Parallelism is about **simultaneous execution**.

------------------------------------------------------------------------

# 3. What Python is actually doing

## A. Threads

``` mermaid
flowchart TB
    P[One Python process] --> M[(Shared process memory)]
    P --> T1[Thread 1]
    P --> T2[Thread 2]
    P --> T3[Thread 3]
    T1 --> M
    T2 --> M
    T3 --> M
```

-   Threads live inside one process.
-   They share memory, so sharing data is easy---but concurrent writes
    may need locks.
-   A thread blocked on I/O does not need to stop other threads from
    doing useful work.
-   In standard GIL-enabled CPython, threads usually do not run
    pure-Python bytecode in parallel.

**Good fit:** blocking HTTP/SDK calls, file I/O, legacy libraries
without async support.

## B. Processes

``` mermaid
flowchart TB
    subgraph OS[Operating system]
      P1[Process 1<br/>Python interpreter<br/>Own memory]
      P2[Process 2<br/>Python interpreter<br/>Own memory]
      P3[Process 3<br/>Python interpreter<br/>Own memory]
    end
    P1 <-->|IPC / serialized data| P2
    P2 <-->|IPC / serialized data| P3
```

-   Each process has its own memory space and Python interpreter.
-   Processes can execute Python CPU work on different cores.
-   Passing data between processes costs time: serialization, copying
    and IPC.
-   Starting processes also has overhead.

**Good fit:** CPU-heavy Python calculations, isolated workers,
independent jobs.

## C. Asyncio

``` mermaid
flowchart TD
    E[Event loop] --> A[Coroutine A]
    E --> B[Coroutine B]
    E --> C[Coroutine C]
    A -->|await network response| E
    B -->|await database response| E
    C -->|await file operation| E
    E -->|resume when ready| A
    E -->|resume when ready| B
    E -->|resume when ready| C
```

-   Usually one event-loop thread manages many coroutines.
-   A coroutine runs until it reaches an `await` that suspends it.
-   The event loop then schedules another ready coroutine.
-   If you call a blocking function or perform a long CPU loop, the
    event loop cannot switch to other coroutines on that thread.

**Good fit:** many concurrent network/database operations when
async-compatible libraries are available.

------------------------------------------------------------------------

# 4. The GIL: why threads behave differently for CPU work

In standard GIL-enabled CPython, the Global Interpreter Lock allows only
one thread at a time to execute Python bytecode within an interpreter.

``` mermaid
flowchart LR
    subgraph Threads[Threads in one process]
      T1[Thread A]
      T2[Thread B]
      T3[Thread C]
    end
    T1 --> G[GIL]
    T2 --> G
    T3 --> G
    G --> CPU[Python bytecode execution]
```

For pure-Python CPU work, threads take turns acquiring the GIL. Adding
more threads does not normally create CPU parallelism.

With processes, each process has its own interpreter and GIL:

``` mermaid
flowchart LR
    P1[Process 1 + GIL] --> C1[CPU core]
    P2[Process 2 + GIL] --> C2[CPU core]
    P3[Process 3 + GIL] --> C3[CPU core]
```

### GIL nuance worth saying in interviews

-   The usual explanation applies to **standard GIL-enabled CPython**.
-   Some native extensions release the GIL while doing work; threads can
    then help.
-   Free-threaded CPython builds also exist, so avoid claiming that
    every Python implementation always has this limitation.

------------------------------------------------------------------------

# 5. Connect the theory to your benchmark

Your lab simulated two different kinds of work:

1.  I/O: each task waits for one second.
2.  CPU: each task performs a Python calculation loop.

## Your observed I/O timings

  ------------------------------------------------------------------------
  Execution model                      Measured time What happened
  --------------------- ---------------------------- ---------------------
  Sequential                                 6.025 s Six waits happened
                                                     one after another

  Thread pool, 4                             2.011 s Four waits
  workers                                            overlapped; then two
                                                     more

  Asyncio                                    1.003 s All six coroutine
                                                     waits overlapped
  ------------------------------------------------------------------------

``` text
Sequential       ██████████████████████████████  6.025 s
Thread pool      ██████████                      2.011 s
Asyncio          █████                           1.003 s
                 0       2       4       6 seconds
```

### Why does this happen?

With six independent one-second waits:

-   Sequential: `6 × 1s ≈ 6s`
-   Four threads: `ceil(6 / 4) × 1s ≈ 2s`
-   Asyncio: six waits can overlap, so `≈ 1s`

This benchmark uses `time.sleep()` for sequential/threaded work and
`asyncio.sleep()` for async work. It demonstrates blocking vs
non-blocking waiting; it is not a real HTTP benchmark.

## Your observed CPU timings

  ------------------------------------------------------------------------
  Execution model                      Measured time Interpretation
  --------------------- ---------------------------- ---------------------
  Sequential                                 0.318 s Baseline

  Thread pool                                0.304 s No meaningful CPU
                                                     speedup

  Process pool                               0.317 s Workload too small to
                                                     offset process
                                                     overhead
  ------------------------------------------------------------------------

``` text
Sequential       ██████████████████████████████  0.318 s
Thread pool      █████████████████████████████   0.304 s
Process pool     ██████████████████████████████  0.317 s
                 0.00    0.10    0.20    0.30 seconds
```

**The important learning:** multiprocessing is not automatically faster.
The task must be large enough to justify process startup and
communication overhead.

### What should you try next?

``` bash
# Increase CPU work so the computation is large compared with process overhead
python concurrency_lab.py --tasks 6 --workers 4 --iterations 30000000

# Compare worker counts
python concurrency_lab.py --tasks 20 --workers 2 --iterations 10000000
python concurrency_lab.py --tasks 20 --workers 4 --iterations 10000000
python concurrency_lab.py --tasks 20 --workers 8 --iterations 10000000
```

Use the exact argument names shown by `python concurrency_lab.py --help`
if your local script differs. Run multiple trials and compare median
times; one run is not a reliable benchmark.

------------------------------------------------------------------------

# 6. How to read PID and TID

The lab prints a process ID (PID) and thread ID (TID).

  -----------------------------------------------------------------------
  What you see                        Meaning
  ----------------------------------- -----------------------------------
  Same PID, different TIDs            Different threads in one process

  Different PIDs                      Separate processes

  Same PID/TID across asyncio tasks   Coroutines sharing an event-loop
                                      thread
  -----------------------------------------------------------------------

``` text
Thread pool
PID 1000 ── TID 2001: Task A
         ├─ TID 2002: Task B
         └─ TID 2003: Task C

Process pool
PID 1000 ── Task A
PID 1001 ── Task B
PID 1002 ── Task C

Asyncio
PID 1000 / TID 2001 ── Coroutine A, B, C take turns
```

A TID number may coincidentally be the same in different processes.
Always compare PID and TID together.

------------------------------------------------------------------------

# 7. Apply it to a real FastAPI service

Consider an API endpoint that receives a request, calls two external
services, performs a calculation, and returns a response.

``` mermaid
flowchart TD
    R[Incoming request] --> A[FastAPI endpoint]
    A --> B[Call service A]
    A --> C[Call service B]
    B --> D[Wait for network response]
    C --> E[Wait for network response]
    D --> F[Combine results]
    E --> F
    F --> G{CPU-heavy calculation?}
    G -->|No| H[Return response]
    G -->|Yes| I[Bounded process / worker pool]
    I --> H
```

## Async endpoint: good for async I/O

``` python
@app.get("/profile")
async def profile():
    user, orders = await asyncio.gather(
        user_client.get_user(),
        order_client.get_orders()
    )
    return {"user": user, "orders": orders}
```

Both calls can be in flight while the event loop serves other work. The
clients must genuinely support async I/O.

## Blocking SDK inside async endpoint: a trap

``` python
@app.get("/bad")
async def bad_endpoint():
    result = synchronous_sdk_call()  # Blocks this event-loop thread
    return {"result": result}
```

The `async` keyword does not make `synchronous_sdk_call()` non-blocking.

Move blocking work to a bounded thread pool, or use an async-compatible
client.

## CPU-heavy work: do not run it directly on the event loop

``` python
@app.post("/analyze")
async def analyze(payload: dict):
    result = await run_in_process_pool(payload)
    return {"result": result}
```

`run_in_process_pool` is a conceptual placeholder: in a real service,
use a long-lived, bounded process pool or a separate worker service. Do
not create a new process pool for every request.

------------------------------------------------------------------------

# 8. Production architecture: from request to worker

For long-running or bursty work, avoid making every API request perform
the entire job inline.

``` mermaid
flowchart LR
    U[Client] --> API[FastAPI]
    API -->|validate + enqueue| Q[(Job queue)]
    API -->|job ID| U
    Q --> W1[Worker 1]
    Q --> W2[Worker 2]
    Q --> W3[Worker N]
    W1 --> DB[(Result store)]
    W2 --> DB
    W3 --> DB
    U -->|poll / callback| API
    API --> DB
```

### Why introduce a queue?

  Problem          Queue/worker benefit
  ---------------- -----------------------------------------------------
  Traffic bursts   Jobs wait instead of overwhelming workers
  Slow tasks       API can return a job ID quickly
  Worker crash     Jobs can be retried according to policy
  Scaling          Add workers independently of API servers
  Backpressure     Queue depth and worker capacity can regulate intake

A queue is not magic: define maximum queue size, expiry, retry limits,
dead-letter handling and overload behavior.

------------------------------------------------------------------------

# 9. System-design decision table

  -----------------------------------------------------------------------
  Situation               First option to         Watch out for
                          consider                
  ----------------------- ----------------------- -----------------------
  Thousands of outbound   Async I/O               Connection limits, rate
  API calls                                       limits, timeouts

  Blocking vendor SDK     Thread pool             Bound the number of
                                                  threads

  Pure-Python CPU work    Process pool            Serialization and
                                                  startup overhead

  Long-running jobs       Queue + workers         Retries, idempotency,
                                                  dead letters

  GPU inference           Dedicated inference     GPU memory, batching,
                          server                  queue latency

  Small one-off script    Sequential code         Do not over-engineer
  -----------------------------------------------------------------------

### A practical design checklist

1.  Identify the bottleneck: I/O, CPU, GPU, database or downstream rate
    limit.
2.  Choose the execution model that matches it.
3.  Set a concurrency limit; do not allow unlimited work.
4.  Set timeouts and cancellation behavior.
5.  Add backpressure when downstream capacity is exhausted.
6.  Measure queue wait, execution time, throughput and p95/p99 latency.
7.  Load-test realistic request sizes and traffic patterns.

------------------------------------------------------------------------

# 10. Interview practice: answer with the right mental model

```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q1. Concurrency vs parallelism?`</strong>`{=html}
```{=html}
</summary>
```
Concurrency means multiple tasks make progress over overlapping periods.
Parallelism means multiple tasks execute at the same instant, typically
on different CPU cores.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q2. When would you use asyncio instead of
threads?`</strong>`{=html}
```{=html}
</summary>
```
I use asyncio for high-concurrency I/O when the libraries support async
operations. I use threads when integrating blocking I/O libraries.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q3. Why don't Python threads speed up CPU-bound
code?`</strong>`{=html}
```{=html}
</summary>
```
In standard GIL-enabled CPython, threads cannot normally execute Python
bytecode in parallel within one interpreter. For pure-Python CPU work, I
consider multiprocessing.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q4. Does async mean parallel
execution?`</strong>`{=html}
```{=html}
</summary>
```
No. Asyncio provides cooperative concurrency. A single event loop
usually runs on one thread; CPU-heavy work must be moved elsewhere to
run in parallel.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q5. How would you handle 10,000 simultaneous API
requests?`</strong>`{=html}
```{=html}
</summary>
```
I would use async I/O, connection pooling, bounded concurrency, timeouts
and rate limits. CPU-heavy or long-running work would go to worker
processes or a queue. I would scale based on load-test results and
bottleneck metrics.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q6. How do you handle a sudden burst of background
jobs?`</strong>`{=html}
```{=html}
</summary>
```
I would enqueue jobs, cap queue growth, scale workers based on queue
depth and processing rate, and define retry, timeout and dead-letter
policies. The API should not execute every job inline.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q7. Why can multiprocessing be slower for small
tasks?`</strong>`{=html}
```{=html}
</summary>
```
Process startup, serialization and inter-process communication add
overhead. The computation must be large enough to outweigh those costs.
```{=html}
</details>
```
```{=html}
<details>
```
```{=html}
<summary>
```
`<strong>`{=html}Q8. Does FastAPI async def guarantee non-blocking
execution?`</strong>`{=html}
```{=html}
</summary>
```
No. It only helps when the endpoint awaits non-blocking operations.
Synchronous blocking calls inside it can block the event loop.
```{=html}
</details>
```

------------------------------------------------------------------------

# 11. The 30-second answer to memorize

> I choose the execution model based on the bottleneck. For I/O-bound
> workloads, I use asyncio when dependencies support non-blocking
> operations, or threads for blocking I/O. For CPU-bound pure-Python
> workloads, I use processes to achieve parallel execution across cores.
> In production, I also use bounded pools, queues, timeouts and
> backpressure, and validate the design using realistic load tests and
> latency and throughput metrics.

------------------------------------------------------------------------

# 12. Final mental map

``` text
                         PYTHON WORK
                              |
                 +------------+------------+
                 |                         |
              I/O-BOUND                 CPU-BOUND
                 |                         |
          +------+-------+              Processes
          |              |                 |
       Asyncio         Threads        Multiple processes
          |              |             can use cores
     Async libraries   Blocking I/O
          |
    Event loop switches
    when coroutine awaits

       PRODUCTION LAYER AROUND ALL OF THEM
       -----------------------------------
       Limits • Queues • Timeouts • Retries
       Backpressure • Metrics • Load tests
```

## Benchmark caveats

This is a learning exercise, not a production capacity test:

-   `asyncio.sleep()` simulates a non-blocking wait; it is not a real
    network request.
-   `time.sleep()` simulates blocking I/O; it is not a real database or
    file operation.
-   The CPU loop is synthetic.
-   Process-pool startup may be included in the timing, depending on the
    script structure.
-   Results depend on Python version, OS, machine load, CPU and worker
    count.
-   Standard CPython GIL behavior described here refers to GIL-enabled
    builds.

**Use the benchmark to understand the mechanics---not to claim a
production speedup.**

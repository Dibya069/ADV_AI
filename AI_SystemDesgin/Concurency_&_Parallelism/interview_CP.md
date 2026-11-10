For AI System Design, the most important thing is understanding when to use concurrency, when to use parallelism, and which execution model fits the workload.

Your six experiments cover the major execution strategies in Python. Let's connect each one to real-world AI production systems.

# 1. Understand the six execution models

First, divide them into two categories.

Concurrency vs Parallelism

Concurrency

Handle multiple tasks by making progress on them during overlapping periods.

![Demystifying Parallelism vs. Concurrency with Processes and Threads | by Tai | Medium](https://images.openai.com/static-rsc-4/z1TC1vWmtve5RfbwnUV3rNytOTt7eJK115Dt5L1PRy8bsCobC-h-0l8JcESWHzqj8rcy3Kies4vDLQtWCZcW5rD_0jgoCUQQFHAUenKmpMr3a83rAQLCFemCbXxz9vAJBtC5mY31yZCA1QSgzJB9D4wEP-Uc0LYfhwtu2FEhMQ4?purpose=inline)

Tasks take turns or yield while waiting.

Parallelism

Execute multiple tasks at exactly the same time.

![Chapter 4: Threads. -  ppt download](https://images.openai.com/static-rsc-4/VnoQWGS6i3pMOPBo5ZBLVsSQx8A--Cy1fx-oIr4QI0wUbEE-u3FiFLkuEgzkgnDPvB3o8QLhHeh0RLRch-_AmBeRM_KGy4p16_QAmOtSiaLE8dHs4QAFgXdN2nwL21PR0HhT7obMwN8pEmEhqiFSi1F8Lbj3WI738gLPLiiYa7Y?purpose=inline)

Tasks execute simultaneously on multiple cores or processors.

Simple distinction:

- Concurrency = managing multiple tasks.
- Parallelism = executing multiple tasks simultaneously.

# 2. When should you use each of the six approaches?

## A. I/O-bound workloads

I/O-bound means your application spends most of its time waiting for external resources.

Examples:

- API requests
- Database queries
- Vector database retrieval
- File downloads
- LLM API calls
- Network communication

1\. Sequential I/O

Use for simple, dependent tasks

![Concurrent Programming Notes Part 2: Understanding Serial vs Parallel Execution | by Bahadır AKDEMİR | Medium](https://images.openai.com/static-rsc-4/s3qauDECvT-H4LcpD4-jFUWy_hP4KefFMH7zH96adv-MHgmnm7AWJDprtVN1tiJ7MsV0Gd51Z72AoZ8aCRYKnGbR95oYPQdcc4zEPxes_j8zsFbVv0R_fCu2TcDoJ59yp_ccvFoCVGgrzCW-8-O4mxjF28VhAjQXX_kQUYhvf10?purpose=inline)

![medium.com](https://medium.com/%40akdemir_bahadir/concurrent-programming-notes-part-2-understanding-serial-vs-parallel-execution-97c87358631f?utm_source=chatgpt.com)

Scenario: You need to call three APIs, and each API depends on the previous API's response.

```
result1 = await api1()result2 = await api2(result1)result3 = await api3(result2)
```

When: Tasks are dependent, or there are very few operations and simplicity matters.

2\. Threaded I/O — ThreadPoolExecutor

Use for blocking I/O

![Custom Executor Service With Metrics | by Soumya Acharya | Medium](https://images.openai.com/static-rsc-4/HE7BjwKmPRSk7ipdi-HoB4V5ujSYpKShMa9IZkpbckgGXZrz6v9kott6xlEnXLplxGc2U6tyHgeuFqW0mJVOtUZCVdPQheaefsp4T2bFDzvbtf8oNgZWO3EdTr-RHYAr9g_xaNYiNUvyXUpHSK1zYrOTy4ppbG9xm9yoIl-ED90?purpose=inline)

![medium.com](https://medium.com/%40cse.soumya/custom-executor-service-with-metrics-8f9802468eec?utm_source=chatgpt.com)

Scenario: You have multiple blocking HTTP requests or a synchronous database driver.

```
from concurrent.futures import ThreadPoolExecutorwith ThreadPoolExecutor(max_workers=5) as pool:    results = list(pool.map(fetch_api, urls))
```

When:

- Legacy synchronous libraries.
- Blocking API calls.
- File operations.
- Synchronous SDKs.

Why: While one thread waits for I/O, another thread can execute.

3\. Asyncio I/O

Best for high-concurrency async I/O

![Python Async Programming: The Complete Guide | DataCamp](https://images.openai.com/static-rsc-4/zvrbIBadQJNePHJ-st1NbQ4r9l9yaM-muuzVTyWatXDFOQWeWrgwDNhbixF-oouuq2aCUo6-ecjz_gVvNwFVfp7mqW3tQzGOGeW3-tCUVs-y3ixbQmoCQV48x2nOiX6yWOn0KxSyvrwgKyTkM6rLijL8u0hH1A-QkP7p87gw2wM?purpose=inline)

![datacamp.com](https://www.datacamp.com/tutorial/python-async-programming?utm_source=chatgpt.com)

Scenario: Your AI application receives 1,000 concurrent requests and each request calls multiple external services.

```
import asyncioresults = await asyncio.gather(    api1(),    api2(),    api3())
```

When:

- FastAPI applications.
- Multiple LLM API calls.
- Async database and vector DB clients.
- High-concurrency network services.
- Streaming responses.

Why: One event loop efficiently manages many waiting operations without requiring one thread per request.

## B. CPU-bound workloads

CPU-bound means your application spends most of its time performing computations.

Examples:

- Image processing
- Audio processing
- Embedding preprocessing
- Large-scale data transformations
- Complex mathematical calculations

4\. Sequential CPU

Use for small workloads

![Identify the Advantages of Concurrency and Parallelism - OpenClassrooms](https://images.openai.com/static-rsc-4/raYREz6fElYdnDV2AR6zc1SukRw_dgb4dKYZehYndtficJRABZf5uMf-HLLeZcP7LmdyTCy-2HRp6oewl0Lu1yrI_334ajKZTODLYvWmPSp2_VhvmhVa3UiI7ON4yM1Kp2trlQbQ9pUag3SR8-uxzgUBbOJvik-Ho24Y6ZDWxyM?purpose=inline)

![openclassrooms.com](https://openclassrooms.com/en/courses/5684021-scale-up-your-code-with-java-concurrency/5684028-identify-the-advantages-of-concurrency-and-parallelism?utm_source=chatgpt.com)

Scenario: Processing a small dataset or running a lightweight calculation.

```
results = [compute(x) for x in data]
```

When: Small workloads, simple logic, or when parallelization overhead is greater than the benefit.

5\. Threaded CPU

Usually not ideal for pure Python CPU work

![Global Interpreter Lock (GIL) in Python – Everything You Need to Know for Interviews - DEV Community](https://images.openai.com/static-rsc-4/WlISOuxIoQkoDVNUa6uoLfnW-GJlGGvLnR01t_1oy-z5kTAGAtPIEJRsVp38xHHBC23eVnqEJPbPOHNA8ibHkc0gyGRk596cyDKJOp7COJ1fgSbiRgQ6dBpQF61MMmtmzHtbqmNg8MefgN91QcoM0reCKqw4s47_pfW36sLwnG4?purpose=inline)

![dev.to](https://dev.to/imsushant12/global-interpreter-lock-gil-in-python-everything-you-need-to-know-for-interviews-5e4g?utm_source=chatgpt.com)

Scenario: Multiple Python threads performing CPU-intensive calculations.

```
with ThreadPoolExecutor(max_workers=4) as pool:    results = list(pool.map(compute, data))
```

When:

- CPU operations release the GIL.
- NumPy operations implemented in native code.
- Some image-processing libraries.
- Native ML libraries that handle their own parallelism.

Important: In conventional CPython, the GIL prevents multiple threads from simultaneously executing Python bytecode. Therefore, pure Python CPU workloads generally don't scale across cores using threads.

6\. Multiprocessing CPU

Best for CPU-heavy independent tasks

![An introduction to parallel programming using Python’s multiprocessing module | Sebastian Raschka, PhD](https://images.openai.com/static-rsc-4/5IDc5WC33R9fmyFQENRTmQppwTqiZHUwQImgM2GPadD53t6w_0JnusRRVSgkL0yeD7q4BXHiNYJXO_XmbiOSDs0EK0LCnckRRP2z5vCOi6b8v-qqefRE3tX1WA0ftSm2Oc5krZlX6ieDGZFogBR2cvIudHWcTT7cb9tjMGiRTwM?purpose=inline)

![sebastianraschka.com](https://sebastianraschka.com/Articles/2014_multiprocessing.html?utm_source=chatgpt.com)

Scenario: Processing thousands of independent audio files or performing CPU-heavy transformations.

```
from concurrent.futures import ProcessPoolExecutorwith ProcessPoolExecutor(max_workers=4) as pool:    results = list(pool.map(compute, data))
```

When:

- Pure Python CPU-intensive workloads.
- Independent data processing.
- CPU-heavy preprocessing.
- Parallel batch processing.

Why: Each process has its own Python interpreter and GIL, allowing execution across multiple CPU cores.

# 3. Decision matrix: Which one should you choose?

This is the table worth remembering for system design interviews.

| Execution model     | Best use case               | AI system example          |
| ------------------- | --------------------------- | -------------------------- |
| Sequential I/O      | Dependent operations        | Chained API calls          |
| Threaded I/O        | Blocking I/O                | Synchronous SDK requests   |
| Asyncio I/O         | High-concurrency I/O        | FastAPI + async LLM APIs   |
| Sequential CPU      | Small computations          | Small data transformations |
| Threaded CPU        | Native code releasing GIL   | NumPy, image processing    |
| Multiprocessing CPU | Pure Python CPU-heavy tasks | Audio preprocessing        |

My practical recommendation:

- Asyncio → Your default for modern asynchronous AI backend orchestration.
- ThreadPoolExecutor → When integrating blocking libraries.
- ProcessPoolExecutor → For CPU-intensive Python workloads.
- Sequential → When operations are dependent or workloads are small.

# 4. Real-world AI system design scenarios

Now let's apply these concepts to actual AI architecture.

## Scenario 1: AI-powered RAG application

Suppose a user sends a query to your RAG application.

You need to:

1. Generate query embedding.
2. Retrieve documents from a vector database.
3. Fetch metadata from PostgreSQL.
4. Call an LLM.
5. Return the response.

Some operations can execute concurrently.

![Vector Databases Explained: pgvector, Pinecone](https://images.openai.com/static-rsc-4/kLN6HkZUP2isytOLHt2lHEHR6Y_eAUpe4gKO4oTJJmdKP6YvseIr8JJLrqLhgGHp00tT0KzFkCEVlT5KdaBGiPyyPFaYjB6ivqmUSZUK7gzeyNsJkSEb0cmz4P6XHNUQY29uu7oWo2qUNCvFl9psgLl_sv8v2cWcbQkAxfhobyw?purpose=inline)

![cloudrps.com](https://cloudrps.com/blog/vector-databases-pgvector-explained/?utm_source=chatgpt.com)

A possible execution strategy:

| Operation                 | Approach                        |
| ------------------------- | ------------------------------- |
| Query embedding           | Async or native model inference |
| Vector retrieval          | Asyncio                         |
| Metadata retrieval        | Asyncio                         |
| Combine retrieved results | Sequential                      |
| LLM API call              | Asyncio                         |
| Response streaming        | Asyncio                         |

Example:

```
async def rag_pipeline(query):    embedding = await generate_embedding(query)    vector_task = retrieve_vectors(embedding)    metadata_task = retrieve_metadata(query)    documents, metadata = await asyncio.gather(        vector_task,        metadata_task    )    context = combine(documents, metadata)    response = await llm.generate(context)    return response
```

Notice that vector retrieval and metadata retrieval happen concurrently.

## Scenario 2: Real-time speech AI system

Consider your ASR-OTT application.

An incoming audio stream needs:

- Audio preprocessing
- Voice activity detection
- Speech recognition
- Text processing
- AI summarization

![A History of Text-to-Speech: From Mechanical Voices to AI Assistants - Vapi AI Blog](https://images.openai.com/static-rsc-4/M0t8i4UoTH7vRfyyE3vCsaZ8bHsPtVJZsGhs9sREHYwbatxTeO-aGDOkmZHCdH7r9uFqZ9YUpPWw0wf-Kr2C7pnlwN6U7zqFbU7HEt3mEQm0171AFp0pg6rbiM2WYRftVX0O-tmCnYbhZd8puhef-nN9NnYWMmA0i8cRE228iOg?purpose=inline)

![vapi.ai](https://vapi.ai/blog/history-of-text-to-speech?utm_source=chatgpt.com)

Possible execution strategy:

| Component             | Approach                                         |
| --------------------- | ------------------------------------------------ |
| Audio reception       | Asyncio                                          |
| Network streaming     | Asyncio                                          |
| Audio preprocessing   | Threads or multiprocessing, depending on library |
| VAD                   | Native CPU processing                            |
| Whisper inference     | GPU inference                                    |
| Text processing       | Sequential or threads                            |
| LLM summarization API | Asyncio                                          |
| Streaming output      | Asyncio                                          |

Important: GPU inference is a separate consideration. Multiprocessing is not automatically the best solution for GPU workloads.

For GPU inference, you generally want:

- Batching
- Request queues
- GPU scheduling
- Model serving workers
- Backpressure

## Scenario 3: Multiple AI models running simultaneously

Imagine your AI gateway has three models:

- Qwen for primary generation.
- Llama for fallback.
- GPT model for additional evaluation.

You receive 100 requests simultaneously.

A sensible architecture:

![How to Handle Too Many Requests Errors in AI APIs | Select](https://images.openai.com/static-rsc-4/lZepQlgBbIoTdLmEuWw3hxHxgqC67vJP37A7OtwnGt8N8d8Ro-ElrSPQ7N0_UDaXDqE-zYsK7dFfLmRae6b_JValQCj5Jixrzx5RaDalQVP6tZUhCD6KCJNv5vbaa-y6XLZRjcWfpHxHWrwmKJRFElJ8tFaS9_FKTGWHH3yHxxg?purpose=inline)

![select.ax](https://select.ax/blog/too-many-requests?utm_source=chatgpt.com)

| Component                          | Approach                         |
| ---------------------------------- | -------------------------------- |
| Incoming requests                  | Asyncio                          |
| Request validation                 | Sequential                       |
| Model selection                    | Sequential                       |
| Concurrent independent model calls | Asyncio                          |
| GPU inference                      | Dedicated model-serving workers  |
| CPU-heavy preprocessing            | Multiprocessing if justified     |
| Fallback                           | Sequential after primary failure |

One important design decision: don't execute all three models for every request unless you genuinely need parallel evaluation. Otherwise, you waste GPU resources and increase cost.

# 5. Production-level considerations

Choosing the execution model is only the beginning. In production, you must also consider:

| Problem                    | Solution                               |
| -------------------------- | -------------------------------------- |
| Too many incoming requests | Bounded queues                         |
| GPU overload               | Dynamic batching and admission control |
| Thread exhaustion          | Limit thread pool size                 |
| Process memory overhead    | Control worker count                   |
| API rate limits            | Semaphore and rate limiter             |
| Slow downstream service    | Timeout                                |
| Failed external requests   | Retry with exponential backoff         |
| Uneven workload            | Load balancing                         |
| Overloaded service         | Backpressure                           |

One particularly important distinction for AI systems:

Asyncio does not make your LLM inference faster. It helps your application handle other requests while waiting for inference to complete.

Similarly, multiprocessing does not automatically improve GPU inference throughput. GPU batching and efficient model serving are usually more relevant.

# 6. Interview cheat sheet

Memorize these six scenarios:

## Which execution model would you choose?

1\. You need to make 500 independent HTTP API calls using an asynchronous client.

Sequential I/O

ThreadPoolExecutor

Asyncio

2\. You have a synchronous third-party SDK that blocks during network requests.

Sequential CPU

ThreadPoolExecutor

Multiprocessing

3\. You need to calculate a CPU-heavy result for 10,000 independent Python objects.

Asyncio

ThreadPoolExecutor

Multiprocessing

4\. You have a FastAPI application waiting for multiple database and LLM API responses.

Asyncio

Multiprocessing

Sequential CPU

5\. You have a tiny CPU calculation that takes 1 millisecond.

Multiprocessing

Sequential CPU

ThreadPoolExecutor

6\. You have a NumPy operation that releases the GIL.

ThreadPoolExecutor

Sequential I/O

Asyncio only

Check answersReset

My final takeaway: For modern AI backend system design, think in three layers:

1. Application concurrency: Asyncio for API requests, database calls and orchestration.
2. CPU parallelism: Multiprocessing or native multithreading for CPU-heavy operations.
3. Model inference parallelism: GPU batching, model workers and request scheduling.

These three layers together are what you need to understand when designing a production-grade AI system.
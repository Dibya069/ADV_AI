
import os
import json
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY is missing")

URL = "https://api.groq.com/openai/v1/chat/completions"


def groq_request(prompt):

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    timing_format = (
        '{"dns":%{time_namelookup},'
        '"tcp_total":%{time_connect},'
        '"tls_total":%{time_appconnect},'
        '"ttfb":%{time_starttransfer},'
        '"total":%{time_total},'
        '"http_code":%{http_code},'
        '"size_download":%{size_download}}'
    )

    with tempfile.NamedTemporaryFile() as response_file:

        command = [
            "curl",
            "-sS",
            "--connect-timeout", "10",
            "--max-time", "120",
            "-X", "POST",
            URL,
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(payload),
            "-o", response_file.name,
            "-w", timing_format
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr)

        timings = json.loads(result.stdout)

        response_file.seek(0)
        body = response_file.read().decode("utf-8")

    response = json.loads(body)

    if timings["http_code"] < 200 or timings["http_code"] >= 300:
        raise RuntimeError(
            f"Groq API error ({timings['http_code']}): {body}"
        )

    # Convert seconds to milliseconds
    dns = timings["dns"] * 1000

    tcp = (
        timings["tcp_total"] - timings["dns"]
    ) * 1000

    tls = (
        timings["tls_total"] - timings["tcp_total"]
    ) * 1000

    ttfb = timings["ttfb"] * 1000

    # Approximate wait after connection and TLS setup
    server_wait = (
        timings["ttfb"] - timings["tls_total"]
    ) * 1000

    transfer = (
        timings["total"] - timings["ttfb"]
    ) * 1000

    total = timings["total"] * 1000

    metrics = {
        "DNS_ms": round(dns, 3),
        "TCP_ms": round(tcp, 3),
        "TLS_ms": round(tls, 3),
        "TTFB_ms": round(ttfb, 3),
        "Server_wait_after_TLS_ms": round(server_wait, 3),
        "TXFER_ms": round(transfer, 3),
        "RTT_ms": round(total, 3),
        "HTTP_status": timings["http_code"],
        "Response_size_bytes": timings["size_download"]
    }

    print("\n========== GROQ RESPONSE ==========\n")

    print(response["choices"][0]["message"]["content"])

    print("\n========== TOKEN USAGE ==========\n")

    print(json.dumps(response.get("usage", {}), indent=4))

    print("\n========== NETWORK METRICS ==========\n")

    print(json.dumps(metrics, indent=4))

    return response, metrics


if __name__ == "__main__":

    prompt = input("Enter your prompt: ")

    groq_request(prompt)

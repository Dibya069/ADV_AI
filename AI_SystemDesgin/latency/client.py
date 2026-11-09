import subprocess
import json
import tempfile
import os
import sys


def make_request(url):

    with tempfile.NamedTemporaryFile() as response_file:

        curl_format = (
            '{"dns":%{time_namelookup},'
            '"connect":%{time_connect},'
            '"tls_connect":%{time_appconnect},'
            '"ttfb":%{time_starttransfer},'
            '"total":%{time_total},'
            '"http_code":%{http_code}}'
        )

        command = [
            "curl",
            "-sS",
            "--output", response_file.name,
            "--write-out", curl_format,
            url
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

    dns = timings["dns"] * 1000
    tcp = (timings["connect"] - timings["dns"]) * 1000

    tls = (
        timings["tls_connect"] - timings["connect"]
    ) * 1000 if url.startswith("https://") else 0

    base = timings["tls_connect"] if url.startswith("https://") else timings["connect"]

    server_wait = (timings["ttfb"] - base) * 1000

    txfer = (
        timings["total"] - timings["ttfb"]
    ) * 1000

    rtt = timings["total"] * 1000

    try:
        response = json.loads(body)
    except json.JSONDecodeError:
        response = body

    # Server processing time is measured independently.
    # Requires the server to return this response header.
    # For this simple example, we use a separate header request
    # in the implementation below instead.

    return {
        "response": response,
        "timings": {
            "DNS_ms": round(dns, 3),
            "TCP_ms": round(tcp, 3),
            "TLS_ms": round(tls, 3),
            "Server_wait_ms": round(server_wait, 3),
            "TXFER_ms": round(txfer, 3),
            "RTT_ms": round(rtt, 3)
        }
    }


if __name__ == "__main__":

    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/test"

    result = make_request(url)

    print(json.dumps(result, indent=4))
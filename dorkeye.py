#!/usr/bin/env python3
import os
import time
import random
import argparse
from rich.console import Console
from rich.progress import Progress
from duckduckgo_search import DDGS

console = Console()

ASCII_LOGO = """
     \n[bold yellow]  ___[/bold yellow][bold red]
 [bold yellow]__H__[/bold yellow]  [bold white]    Advanced Dorking Tool [/bold white]
 [bold yellow] [[/bold yellow][bold red],[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red])[/bold red][bold yellow]][/bold yellow]
 [bold yellow] [[/bold yellow][bold red];[/bold red][bold yellow]][/bold yellow][bold yellow]    DorkEye[/bold yellow]
 [bold yellow] |_|[/bold yellow]  [bold red]  ᵛ²ˑ⁴_ˣᴾˡᵒⁱᵗˢ³ᶜ [/bold red]
 [bold yellow]  V[/bold yellow]
    \n[bold red]Legal disclaimer:[/bold red][bold yellow] attacking targets without prior mutual consent is illegal.[/bold yellow]
[bold red][!][/bold red][bold yellow] It is the end user's responsibility to obey all applicable local, state and federal laws.[/bold yellow]
"""

def print_logo():
    console.print(ASCII_LOGO, style="bold cyan")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 13_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1 Mobile/15E148 Safari/604.1"
]

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
        "Connection": "keep-alive"
    }

def process_input(input_data):
    if os.path.isfile(input_data):
        with open(input_data, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return [input_data]

def write_output(filename, results):
    with open(f"{filename}.csv", "a") as f:
        for i, url in enumerate(results, 1):
            f.write(f"{i}. {url}\n")

def begin_search(queries, count, output_file):
    all_results = []
    for index, query in enumerate(queries, start=1):
        console.print(f"\n[bold green][*] Dorks:[/bold green] {query}")
        results = []
        with Progress() as progress:
            task = progress.add_task("[cyan][+] DuckDuckGo", total=count)
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=count):
                    url = r.get("href") or r.get("url")
                    if url:
                        results.append(url)
                        progress.advance(task)
                        if len(results) >= count:
                            break
                             
        results = list(dict.fromkeys(results))
        console.print(f"[bold blue][+] Found {len(results)} results for this dork[/bold blue]")
         
        all_results.extend(results)
        if output_file:
            write_output(output_file, results)
        delay = round(random.uniform(16, 27), 2)
        console.print(f"[yellow][~] Waiting: {delay} seconds for the next dork...[/yellow]")
        time.sleep(delay)

        if index % 2 == 0:
            long_delay = round(random.uniform(85, 110), 2)
            console.print(f"[bold magenta][~] Waiting: {long_delay} seconds, bypass 403 Ratelimit[/bold magenta]")
            time.sleep(long_delay)
             
    return all_results

def main():
    parser = argparse.ArgumentParser(description="Dorking Tool with DuckDuckGo")
    parser.add_argument("-d", "--dork", required=True, help="Dork or file with dorks")
    parser.add_argument("-o", "--output", help="Output file name without extension")
    parser.add_argument("-c", "--count", type=int, default=50, help="Number of results per dork (default=50)")
    args = parser.parse_args()

    print_logo()
    start = time.time()
    queries = process_input(args.dork)
    begin_search(queries, args.count, args.output)
    end = time.time()


    console.print(f"\n[bold yellow][*] Completed in {round(end - start, 2)} seconds[/bold yellow]")
    console.print(f"\n[bold yellow][✓] Result saved successfully[/bold yellow]")

if __name__ == "__main__":
    main()

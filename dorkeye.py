#!/usr/bin/env python3
import os
import time
import argparse
from rich.console import Console
from rich.progress import Progress
from duckduckgo_search import DDGS

console = Console()

ASCII_LOGO = """
     +-+-+-+-+-+-+-+-+
     |D|o|r|k|-|E|y|e|
     +-+-+-+-+-+-+-+-+
     \n[bold red]  ᵛ¹ˑ⁰_ᵇʸ_ˣᴾˡᵒⁱᵗˢ³ᶜ [/bold red]

     \n[bold red]Legal disclaimer:[/bold red] attacking targets without prior mutual consent is illegal.
     \n[bold yellow][!][/bold yellow] It is the end user's responsibility to obey all applicable local, state and federal laws.
"""

def print_logo():
    console.print(ASCII_LOGO, style="bold cyan")

def process_input(input_data):
    if os.path.isfile(input_data):
        with open(input_data, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return [input_data]

def write_output(filename, results):
    with open(f"{filename}.txt", "a") as f:
        for i, url in enumerate(results, 1):
            f.write(f"{i}. {url}\n")

def begin_search(queries, count, output_file):
    all_results = []
    for query in queries:
        console.print(f"\n[bold green][I] Dorks:[/bold green] {query}")
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
        all_results.extend(results)
        if output_file:
            write_output(output_file, results)
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


    console.print(f"\n[bold yellow][I] Completed in {round(end - start, 2)} seconds[/bold yellow]")
    console.print(f"\n[bold yellow][I] Result saved successfully[/bold yellow]")

if __name__ == "__main__":
    main()

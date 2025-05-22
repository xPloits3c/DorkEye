General Description

Dork-Eye is a Python script for ethical dorking, i.e. advanced search for information online using search operators (“Google/DuckDuckGo Dorks”). The goal is to identify unintentionally exposed resources, such as sensitive files, login panels or indexed directories.

This script is based on DuckDuckGo as an alternative search engine to Google, using the duckduckgo_search library to obtain results anonymously and without anti-bot blocks.

Main Features

Feature Details
Single or file input support Accepts a single dork or a .txt file containing multiple dorks
File output Saves results to optional .txt file
Progress counter Displays progress with rich.Progress
Anonymous search Use duckduckgo_search.DDGS() to avoid rate-limiting and CAPTCHA
Logo & disclaimer Displays an ASCII banner and legal notice
CLI with argparse Simple and effective terminal interface

Code Structure

1. Banner and Disclaimer

The script displays a custom banner in underground hacker style and a legal disclaimer to reiterate the user's responsibility.

console.print(ASCII_LOGO, style="bold cyan")

2. Input Handling

The -d parameter can be:
• A single dork
• A text file with one dork per line

def process_input(input_data):
...

This flexibility is useful for running automated attacks or massive tests.

3. Search Engine

Using DuckDuckGo (via DDGS()) allows to bypass limitations imposed by Google, making the tool more resilient and anonymous.

with DDGS() as ddgs:
for r in ddgs.text(query, max_results=count):
...

Multiple results for each dork are collected, filtered and optionally saved.

4. Saving Results

If the -o argument is passed, the results are saved to an output.txt file.

def write_output(filename, results):
...

5. Progress and Feedback

Progress is displayed dynamically with an animated text interface thanks to rich.progress.

with Progress() as progress:
task = progress.add_task("[cyan]⏳ DuckDuckGo", total=count)

Usage

Example Runs:

Single dork

python3 dork-eye.py -d 'inurl:login.php' -o results -c 100

Files with multiple dorks

python3 dork-eye.py -d dorks.txt -o vuln_sites -c 30

Possible Future Improvements
1. Filters by extension or domain (.pdf, .php, .gov, etc.)
2. CSV or JSON export of results
3. Automatically scan URLs found (e.g. with requests or Wappalyzer)
4. Coloring of results by severity (based on the type of URL found)
5. Support for other engines (e.g. Bing, Brave Search)
6. Interactive interface (TUI mode with Textual)

Legal Notice

This script should not be used for illegal purposes. It is intended for:
• Security testing
• Authorized pentesting
• Academic or educational research
The author is not responsible for improper use.

Conclusion

Dork-Eye is an excellent starting point for those who want to automate dorking in an ethical and anonymous way. The combination of Python, duckduckgo_search and rich makes it lightweight, fast and visually effective.

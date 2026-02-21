import re
from bs4 import BeautifulSoup

def analyze():
    try:
        with open("debug_page.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print("HTML file not found.")
        return

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=re.compile(r"slitmCd=\d+"))
    
    codes = {}
    for a in links:
        match = re.search(r"slitmCd=(\d+)", a["href"])
        if match:
            code = match.group(1)
            text = a.get_text(strip=True)
            if code not in codes:
                codes[code] = []
            codes[code].append(text)

    print(f"Total slitmCd links: {len(links)}")
    print(f"Unique product codes: {len(codes)}")
    
    # Check for time patterns
    time_pattern = re.compile(r"\d{2}:\d{2}\s*~\s*\d{2}:\d{2}")
    times = time_pattern.findall(html)
    print(f"Time patterns found: {len(times)}")

    # Sample some codes and their names
    count = 0
    for code, texts in codes.items():
        if count >= 10: break
        # Filter out empty names
        valid_names = [t for t in texts if len(t) > 2]
        print(f"Code: {code}, Names: {valid_names if valid_names else 'NO_NAME_IN_LINK'}")
        count += 1

if __name__ == "__main__":
    analyze()

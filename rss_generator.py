import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from urllib.parse import urljoin

BASE_URL = "https://www.env.go.jp"
PRESS_URL = "https://www.env.go.jp/press/"

# ページ取得
response = requests.get(PRESS_URL, timeout=30)
response.raise_for_status()
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, "html.parser")

# RSS作成
fg = FeedGenerator()
fg.title("環境省 報道発表")
fg.link(href=PRESS_URL)
fg.description("環境省 報道発表 RSS")

# 重複防止
added = set()

# 報道発表一覧のリンク候補を収集
for a in soup.find_all("a", href=True):

    href = a["href"]
    title = a.get_text(strip=True)

    if not title:
        continue

    # 報道発表記事らしいURLだけ採用
    if "/press/" not in href:
        continue

    url = urljoin(BASE_URL, href)

    if url in added:
        continue

    added.add(url)

    fe = fg.add_entry()
    fe.title(title)
    fe.link(href=url)

# feed.xml出力
fg.rss_file("feed.xml")

print(f"{len(added)} 件の報道発表を登録しました")

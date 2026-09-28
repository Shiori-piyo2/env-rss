import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# 環境省 報道発表一覧
URL = "https://www.env.go.jp/press/"

# ページ取得
response = requests.get(URL)
response.encoding = response.apparent_encoding

# HTML解析
soup = BeautifulSoup(response.text, "html.parser")

# RSS作成
fg = FeedGenerator()
fg.title("環境省 報道発表")
fg.link(href=URL)
fg.description("環境省報道発表のRSS")

# リンク取得
links = soup.find_all("a")

count = 0

for link in links:
    href = link.get("href")
    title = link.get_text(strip=True)

    if href and title:
        if href.startswith("/"):
            href = "https://www.env.go.jp" + href

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=href)

        count += 1

        if count >= 20:
            break

# RSS保存
fg.rss_file("feed.xml")

print("RSS作成完了")

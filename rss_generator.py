import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator


# =========================
# 基本設定
# =========================

PRESS_URL = "https://www.env.go.jp/press/"
OUTPUT_FILE = "feed.xml"

# RSSに掲載する最大件数
MAX_ITEMS = 50

# 日本標準時
JST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; env-rss/1.0; "
        "+https://github.com/Shiori-piyo2/env-rss)"
    )
}


# =========================
# 共通処理
# =========================

def get_soup(url):
    """指定したページを取得してBeautifulSoupを返す。"""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    
    response.raise_for_status()
    
    return BeautifulSoup(
response.content,
"html.parser"
)


def is_press_article(url):
    """
    報道発表の記事URLか判定する。

    採用例:
    /press/press_05643.html
    /press/106098_00002.html

    除外例:
    /press/202609.html
    /press/index.html
    """

    parsed = urlparse(url)

    # 環境省以外は除外
    if parsed.netloc not in ("www.env.go.jp", "env.go.jp"):
        return False

    # /press/ 配下以外は除外
    if not parsed.path.startswith("/press/"):
        return False

    filename = parsed.path.rsplit("/", 1)[-1]

    # トップページ等を除外
    if filename in ("", "index.html"):
        return False

    # 月別アーカイブを除外
    # 例: 202609.html、199612.html
    if re.fullmatch(r"\d{6}\.html", filename):
        return False

    # HTML以外を除外
    if not filename.endswith(".html"):
        return False

    # 現行の報道発表URL
    if re.fullmatch(r"press_.+\.html", filename):
        return True

    # 一部の記事で使われているURL
    # 例: 106098_00002.html
    if re.fullmatch(r"\d+_\d+\.html", filename):
        return True

    return False


def get_article_information(url, fallback_title):
    """
    記事ページからタイトル、発表日、カテゴリを取得する。
    取得できない項目は一覧ページの情報などで補う。
    """

    title = fallback_title
    published = None
    category = ""

    try:
        soup = get_soup(url)

        # ページ内の見出しを記事タイトルとして取得
        heading = soup.find("h1")

        if heading:
            heading_text = heading.get_text(
                " ",
                strip=True
            )

            if heading_text and heading_text != "報道発表資料":
                title = heading_text

        page_text = soup.get_text(
            " ",
            strip=True
        )

        # 発表日を抽出
        # 例: 2026年09月25日
        date_match = re.search(
            r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日",
            page_text
        )

        if date_match:
            year, month, day = map(
                int,
                date_match.groups()
            )

            published = datetime(
                year,
                month,
                day,
                0,
                0,
                0,
                tzinfo=JST
            )

        # カテゴリ候補
        category_names = [
            "大臣官房",
            "総合政策",
            "地球環境",
            "水・土壌",
            "大気環境",
            "自然環境",
            "再生循環",
            "保健対策",
            "地域",
        ]

        for category_name in category_names:
            if category_name in page_text:
                category = category_name
                break

    except requests.RequestException as error:
        print(
            f"記事ページを取得できませんでした: "
            f"{url} / {error}"
        )

    return {
        "title": title,
        "url": url,
        "published": published,
        "category": category,
    }


# =========================
# 報道発表一覧の取得
# =========================

print("環境省の報道発表一覧を取得します")

list_soup = get_soup(PRESS_URL)

article_candidates = []
seen_urls = set()

for link in list_soup.find_all("a", href=True):
    title = link.get_text(
        " ",
        strip=True
    )

    if not title:
        continue

    url = urljoin(
        PRESS_URL,
        link["href"]
    )

    # クエリ文字列やページ内位置を除去
    url = url.split("#", 1)[0]
    url = url.split("?", 1)[0]

    if not is_press_article(url):
        continue

    if url in seen_urls:
        continue

    seen_urls.add(url)

    article_candidates.append({
        "title": title,
        "url": url,
    })

    if len(article_candidates) >= MAX_ITEMS:
        break


if not article_candidates:
    raise RuntimeError(
        "報道発表の記事が見つかりませんでした。"
        "環境省サイトの構造が変更された可能性があります。"
    )


# =========================
# 各記事の情報取得
# =========================

articles = []

for number, candidate in enumerate(
    article_candidates,
    start=1
):
    print(
        f"{number}/{len(article_candidates)} "
        f"{candidate['title']}"
    )

    article = get_article_information(
        candidate["url"],
        candidate["title"]
    )

    articles.append(article)


# 発表日の新しい順に並べる
articles.sort(
    key=lambda item: (
        item["published"]
        or datetime(1970, 1, 1, tzinfo=JST)
    ),
    reverse=True
)


# =========================
# RSS作成
# =========================

feed = FeedGenerator()

feed.id(PRESS_URL)
feed.title("環境省 新着報道発表")
feed.link(
    href=PRESS_URL,
    rel="alternate"
)
feed.description(
    "環境省の報道発表一覧から取得した新着情報"
)
feed.language("ja")
feed.generator(
    generator="env-rss",
    version="1.0"
)
feed.lastBuildDate(
    datetime.now(JST)
)

for article in articles:
    entry = feed.add_entry()

    # URLをRSS項目の一意識別子として使用
    entry.id(article["url"])
    entry.title(article["title"])
    entry.link(
        href=article["url"]
    )

    description_parts = []

    if article["category"]:
        description_parts.append(
            f"分野：{article['category']}"
        )

    if article["published"]:
        description_parts.append(
            "発表日："
            + article["published"].strftime(
                "%Y年%m月%d日"
            )
        )

        entry.published(
            article["published"]
        )

    if description_parts:
        entry.description(
            " / ".join(description_parts)
        )
    else:
        entry.description(
            "環境省の報道発表資料"
        )


feed.rss_file(
    OUTPUT_FILE,
    pretty=True
)

print(
    f"完了：{len(articles)}件を"
    f"{OUTPUT_FILE}に出力しました"
)

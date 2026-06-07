from __future__ import annotations

from dataclasses import dataclass
import hashlib
from html import escape
from pathlib import Path
from string import Template
import textwrap
import webbrowser

from .article import Article, body_with_tags, hashtags_for
from .inspect import ArticleReport, inspect_path, inspect_article
from .scaffold import slugify


NOTE_NEW_TEXT_URL = "https://note.com/notes/new"
NOTE_LOGIN_URL = "https://note.com/login"


@dataclass(frozen=True)
class DashboardItem:
    report: ArticleReport
    helper_path: Path


def open_note_login() -> None:
    webbrowser.open(NOTE_LOGIN_URL)


def open_manual_post_helper(
    article: Article,
    *,
    append_tags: bool,
    output_dir: Path,
    open_note: bool = True,
    open_helper: bool = True,
) -> Path:
    html_path = write_manual_post_helper(article, append_tags=append_tags, output_dir=output_dir)
    if open_note:
        webbrowser.open(NOTE_NEW_TEXT_URL)
    if open_helper:
        webbrowser.open(html_path.resolve().as_uri())
    return html_path


def write_manual_post_helper(article: Article, *, append_tags: bool, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{_safe_stem(article)}.html"
    body = body_with_tags(article) if append_tags else article.body
    report = inspect_article(article, append_tags=append_tags)
    html_path.write_text(_helper_html(article, body, report), encoding="utf-8")
    return html_path


def open_manual_dashboard(
    path: Path,
    *,
    pattern: str,
    append_tags: bool,
    output_dir: Path,
    open_note: bool = False,
    open_dashboard: bool = True,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    helper_dir = output_dir / "helpers"
    helper_dir.mkdir(parents=True, exist_ok=True)

    reports = inspect_path(path, pattern=pattern, append_tags=append_tags)
    items = [
        DashboardItem(
            report=report,
            helper_path=write_manual_post_helper(report.article, append_tags=append_tags, output_dir=helper_dir),
        )
        for report in reports
    ]
    dashboard_path = output_dir / "dashboard.html"
    dashboard_path.write_text(_dashboard_html(items), encoding="utf-8")

    if open_note:
        webbrowser.open(NOTE_NEW_TEXT_URL)
    if open_dashboard:
        webbrowser.open(dashboard_path.resolve().as_uri())
    return dashboard_path


def _safe_stem(article: Article) -> str:
    base = slugify(article.source.stem)
    digest = hashlib.sha1(str(article.source.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{base}-{digest}"


def _helper_html(article: Article, body: str, report: ArticleReport) -> str:
    issues = _issues_html(report)
    tags = hashtags_for(article)
    stats = report.stats
    summary = article.summary or _auto_summary(article.body)
    cover = article.cover or "(none)"
    preview = _markdown_preview(body)
    template = Template(
        textwrap.dedent(
            """\
            <!doctype html>
            <html lang="ja">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>auto-note helper</title>
              <style>
                :root {
                  color-scheme: light;
                  font-family: "Segoe UI", system-ui, sans-serif;
                  background: #f6f7f9;
                  color: #17191c;
                }
                body {
                  margin: 0;
                  padding: 24px;
                }
                main {
                  max-width: 1120px;
                  margin: 0 auto;
                }
                header {
                  display: flex;
                  justify-content: space-between;
                  gap: 16px;
                  align-items: center;
                  margin-bottom: 16px;
                }
                h1 {
                  font-size: 22px;
                  margin: 0;
                  font-weight: 650;
                }
                .actions, .copy-row, .tabs {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 8px;
                  align-items: center;
                }
                .metrics {
                  display: grid;
                  grid-template-columns: repeat(4, minmax(120px, 1fr));
                  gap: 10px;
                  margin: 12px 0 16px;
                }
                .metric {
                  background: #ffffff;
                  border: 1px solid #dcdfe5;
                  border-radius: 8px;
                  padding: 10px 12px;
                }
                .metric strong {
                  display: block;
                  font-size: 19px;
                }
                section, aside {
                  background: #ffffff;
                  border: 1px solid #dcdfe5;
                  border-radius: 8px;
                  margin-top: 12px;
                  overflow: hidden;
                }
                .bar {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  gap: 12px;
                  padding: 12px 14px;
                  border-bottom: 1px solid #e7e9ee;
                  background: #fbfbfc;
                }
                h2 {
                  font-size: 14px;
                  margin: 0;
                  font-weight: 650;
                }
                button, a {
                  border: 1px solid #c8ccd4;
                  background: #ffffff;
                  color: #17191c;
                  padding: 8px 12px;
                  border-radius: 6px;
                  font: inherit;
                  cursor: pointer;
                  text-decoration: none;
                  white-space: nowrap;
                }
                button.primary, a.primary {
                  background: #146c5f;
                  border-color: #146c5f;
                  color: #ffffff;
                }
                button.warn {
                  background: #7b4b13;
                  border-color: #7b4b13;
                  color: #ffffff;
                }
                textarea, input {
                  box-sizing: border-box;
                  display: block;
                  width: 100%;
                  border: 0;
                  resize: vertical;
                  padding: 14px;
                  font: 15px/1.65 ui-monospace, "Cascadia Code", Consolas, monospace;
                  color: #17191c;
                  outline: none;
                }
                input {
                  resize: none;
                }
                #title {
                  min-height: 76px;
                }
                #body {
                  min-height: 420px;
                }
                .status {
                  min-height: 22px;
                  color: #146c5f;
                  font-size: 13px;
                }
                .grid {
                  display: grid;
                  grid-template-columns: minmax(0, 1fr) 320px;
                  gap: 14px;
                  align-items: start;
                }
                .side {
                  padding: 14px;
                }
                .side dl {
                  margin: 0;
                }
                .side dt {
                  color: #5b626f;
                  font-size: 12px;
                  margin-top: 12px;
                }
                .side dd {
                  margin: 4px 0 0;
                  overflow-wrap: anywhere;
                }
                .issues {
                  margin: 8px 0 0;
                  padding-left: 18px;
                }
                .issues li {
                  margin: 6px 0;
                }
                .preview {
                  display: none;
                  padding: 18px;
                  line-height: 1.8;
                }
                .preview.active {
                  display: block;
                }
                .editor.hidden {
                  display: none;
                }
                .preview h1, .preview h2, .preview h3 {
                  line-height: 1.35;
                }
                .preview pre {
                  background: #20242a;
                  color: #f6f7f9;
                  padding: 12px;
                  border-radius: 6px;
                  overflow: auto;
                }
                @media (max-width: 860px) {
                  body {
                    padding: 14px;
                  }
                  header, .bar {
                    align-items: flex-start;
                    flex-direction: column;
                  }
                  .grid, .metrics {
                    grid-template-columns: 1fr;
                  }
                }
              </style>
            </head>
            <body>
              <main>
                <header>
                  <h1>auto-note helper</h1>
                  <div class="actions">
                    <a class="primary" href="$note_new_url" target="_blank" rel="noreferrer">note 投稿画面</a>
                    <a href="$note_login_url" target="_blank" rel="noreferrer">ログイン</a>
                  </div>
                </header>
                <div class="status" id="status"></div>

                <div class="metrics">
                  <div class="metric"><strong id="titleCount">$title_chars</strong>タイトル文字</div>
                  <div class="metric"><strong id="bodyCount">$body_chars</strong>本文文字</div>
                  <div class="metric"><strong id="lineCount">$lines</strong>行</div>
                  <div class="metric"><strong id="readTime">$reading_minutes</strong>分目安</div>
                </div>

                <div class="grid">
                  <div>
                    <section>
                      <div class="bar">
                        <h2>タイトル</h2>
                        <div class="copy-row">
                          <button class="primary" data-copy="title">コピー</button>
                          <button data-copy-all="true">全部コピー</button>
                        </div>
                      </div>
                      <textarea id="title">$title</textarea>
                    </section>

                    <section>
                      <div class="bar">
                        <h2>本文</h2>
                        <div class="copy-row">
                          <div class="tabs">
                            <button data-tab="edit">編集</button>
                            <button data-tab="preview">プレビュー</button>
                          </div>
                          <button class="primary" data-copy="body">コピー</button>
                        </div>
                      </div>
                      <div class="editor" id="editor">
                        <textarea id="body">$body</textarea>
                      </div>
                      <div class="preview" id="preview">$preview</div>
                    </section>

                    <section>
                      <div class="bar">
                        <h2>タグ</h2>
                        <button class="primary" data-copy="hashtags">コピー</button>
                      </div>
                      <input id="hashtags" value="$hashtags">
                    </section>
                  </div>

                  <aside>
                    <div class="side">
                      <h2>投稿メモ</h2>
                      <dl>
                        <dt>ファイル</dt>
                        <dd>$source</dd>
                        <dt>概要</dt>
                        <dd>$summary</dd>
                        <dt>カバー</dt>
                        <dd>$cover</dd>
                        <dt>工程</dt>
                        <dd>$status</dd>
                        <dt>公開予定</dt>
                        <dd>$scheduled</dd>
                        <dt>公開URL</dt>
                        <dd>$published_url</dd>
                        <dt>チェック</dt>
                        <dd>$issues</dd>
                      </dl>
                    </div>
                  </aside>
                </div>
              </main>
              <script>
                const status = document.getElementById("status");
                const titleEl = document.getElementById("title");
                const bodyEl = document.getElementById("body");
                const tagsEl = document.getElementById("hashtags");
                const previewEl = document.getElementById("preview");
                const editorEl = document.getElementById("editor");

                function escapeHtml(value) {
                  const map = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"};
                  return value.replace(/[&<>"']/g, function (char) { return map[char]; });
                }

                function renderMarkdown(markdown) {
                  const lines = markdown.split("\\n");
                  let html = "";
                  let paragraph = [];
                  let inList = false;
                  let inCode = false;
                  let code = [];

                  function flushParagraph() {
                    if (paragraph.length) {
                      html += "<p>" + paragraph.map(escapeHtml).join("<br>") + "</p>";
                      paragraph = [];
                    }
                  }
                  function closeList() {
                    if (inList) {
                      html += "</ul>";
                      inList = false;
                    }
                  }

                  for (const line of lines) {
                    if (line.startsWith("```")) {
                      if (inCode) {
                        html += "<pre><code>" + escapeHtml(code.join("\\n")) + "</code></pre>";
                        code = [];
                        inCode = false;
                      } else {
                        flushParagraph();
                        closeList();
                        inCode = true;
                      }
                      continue;
                    }
                    if (inCode) {
                      code.push(line);
                      continue;
                    }
                    if (!line.trim()) {
                      flushParagraph();
                      closeList();
                      continue;
                    }
                    const heading = line.match(/^(#{1,3})\\s+(.*)/);
                    if (heading) {
                      flushParagraph();
                      closeList();
                      const level = heading[1].length;
                      html += "<h" + level + ">" + escapeHtml(heading[2]) + "</h" + level + ">";
                      continue;
                    }
                    if (line.startsWith("- ")) {
                      flushParagraph();
                      if (!inList) {
                        html += "<ul>";
                        inList = true;
                      }
                      html += "<li>" + escapeHtml(line.slice(2)) + "</li>";
                      continue;
                    }
                    paragraph.push(line);
                  }
                  flushParagraph();
                  closeList();
                  if (inCode) {
                    html += "<pre><code>" + escapeHtml(code.join("\\n")) + "</code></pre>";
                  }
                  return html || "<p></p>";
                }

                async function copyText(value, label) {
                  try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                      await navigator.clipboard.writeText(value);
                    } else {
                      throw new Error("clipboard api unavailable");
                    }
                  } catch (error) {
                    const scratch = document.createElement("textarea");
                    scratch.value = value;
                    document.body.appendChild(scratch);
                    scratch.focus();
                    scratch.select();
                    document.execCommand("copy");
                    scratch.remove();
                  }
                  status.textContent = label + "をコピーしました";
                }

                function copyTarget(id) {
                  if (id === "all") {
                    return titleEl.value + "\\n\\n" + bodyEl.value;
                  }
                  return document.getElementById(id).value;
                }

                function updateStats() {
                  const body = bodyEl.value;
                  document.getElementById("titleCount").textContent = titleEl.value.length;
                  document.getElementById("bodyCount").textContent = body.length;
                  document.getElementById("lineCount").textContent = body.split("\\n").length;
                  document.getElementById("readTime").textContent = Math.max(1, Math.round(body.length / 700));
                  previewEl.innerHTML = renderMarkdown(body);
                }

                for (const button of document.querySelectorAll("[data-copy]")) {
                  button.addEventListener("click", function () {
                    const id = button.dataset.copy;
                    const label = id === "title" ? "タイトル" : id === "body" ? "本文" : "タグ";
                    copyText(copyTarget(id), label);
                  });
                }

                for (const button of document.querySelectorAll("[data-copy-all]")) {
                  button.addEventListener("click", function () {
                    copyText(titleEl.value + "\\n\\n" + bodyEl.value, "全部");
                  });
                }

                for (const button of document.querySelectorAll("[data-tab]")) {
                  button.addEventListener("click", function () {
                    const preview = button.dataset.tab === "preview";
                    editorEl.classList.toggle("hidden", preview);
                    previewEl.classList.toggle("active", preview);
                    updateStats();
                  });
                }

                titleEl.addEventListener("input", updateStats);
                bodyEl.addEventListener("input", updateStats);
                tagsEl.addEventListener("input", updateStats);
                updateStats();
              </script>
            </body>
            </html>
            """
        )
    )
    return template.safe_substitute(
        note_new_url=NOTE_NEW_TEXT_URL,
        note_login_url=NOTE_LOGIN_URL,
        title=escape(article.title),
        body=escape(body),
        hashtags=escape(tags),
        source=escape(str(article.source)),
        summary=escape(summary),
        cover=escape(cover),
        status=escape(article.status),
        scheduled=escape(article.scheduled or "(none)"),
        published_url=escape(article.published_url or "(none)"),
        issues=issues,
        preview=preview,
        title_chars=str(stats.title_chars),
        body_chars=str(stats.body_chars),
        lines=str(stats.lines),
        reading_minutes=str(stats.reading_minutes),
    )


def _dashboard_html(items: list[DashboardItem]) -> str:
    rows = []
    for item in items:
        report = item.report
        article = report.article
        status = "OK" if report.ok else "NG"
        issue_count = len(report.issues)
        rows.append(
            "<tr>"
            f"<td><span class=\"badge {status.lower()}\">{status}</span></td>"
            f"<td><a href=\"{escape(item.helper_path.resolve().as_uri())}\">{escape(article.title)}</a>"
            f"<small>{escape(str(article.source))}</small></td>"
            f"<td>{escape(article.status)}</td>"
            f"<td>{escape(article.scheduled)}</td>"
            f"<td>{report.stats.body_chars}</td>"
            f"<td>{report.stats.reading_minutes}</td>"
            f"<td>{escape(', '.join(article.tags))}</td>"
            f"<td>{issue_count}</td>"
            "</tr>"
        )

    template = Template(
        textwrap.dedent(
            """\
            <!doctype html>
            <html lang="ja">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>auto-note dashboard</title>
              <style>
                :root {
                  font-family: "Segoe UI", system-ui, sans-serif;
                  background: #f6f7f9;
                  color: #17191c;
                }
                body {
                  margin: 0;
                  padding: 24px;
                }
                main {
                  max-width: 1180px;
                  margin: 0 auto;
                }
                header {
                  display: flex;
                  justify-content: space-between;
                  gap: 12px;
                  align-items: center;
                  margin-bottom: 16px;
                }
                h1 {
                  margin: 0;
                  font-size: 22px;
                }
                a, button {
                  border: 1px solid #c8ccd4;
                  background: #ffffff;
                  color: #17191c;
                  padding: 8px 12px;
                  border-radius: 6px;
                  text-decoration: none;
                  font: inherit;
                }
                a.primary {
                  background: #146c5f;
                  border-color: #146c5f;
                  color: #ffffff;
                }
                input {
                  box-sizing: border-box;
                  width: 100%;
                  border: 1px solid #c8ccd4;
                  border-radius: 6px;
                  padding: 10px 12px;
                  margin-bottom: 12px;
                  font: inherit;
                }
                table {
                  width: 100%;
                  border-collapse: collapse;
                  background: #ffffff;
                  border: 1px solid #dcdfe5;
                  border-radius: 8px;
                  overflow: hidden;
                }
                th, td {
                  padding: 11px 12px;
                  border-bottom: 1px solid #e7e9ee;
                  text-align: left;
                  vertical-align: top;
                }
                th {
                  background: #fbfbfc;
                  font-size: 13px;
                }
                small {
                  display: block;
                  color: #5b626f;
                  margin-top: 3px;
                  overflow-wrap: anywhere;
                }
                .badge {
                  display: inline-block;
                  min-width: 34px;
                  text-align: center;
                  border-radius: 999px;
                  padding: 3px 8px;
                  font-size: 12px;
                  font-weight: 650;
                }
                .ok {
                  background: #dff3ed;
                  color: #105f54;
                }
                .ng {
                  background: #ffe2df;
                  color: #8b2119;
                }
                @media (max-width: 760px) {
                  body {
                    padding: 14px;
                  }
                  header {
                    flex-direction: column;
                    align-items: flex-start;
                  }
                  table {
                    display: block;
                    overflow-x: auto;
                  }
                }
              </style>
            </head>
            <body>
              <main>
                <header>
                  <h1>auto-note dashboard</h1>
                  <a class="primary" href="$note_new_url" target="_blank" rel="noreferrer">note 投稿画面</a>
                </header>
                <input id="filter" placeholder="検索">
                <table>
                  <thead>
                    <tr>
                      <th>状態</th>
                      <th>記事</th>
                      <th>工程</th>
                      <th>予定</th>
                      <th>文字</th>
                      <th>分</th>
                      <th>タグ</th>
                      <th>指摘</th>
                    </tr>
                  </thead>
                  <tbody id="rows">
                    $rows
                  </tbody>
                </table>
              </main>
              <script>
                const filter = document.getElementById("filter");
                const rows = Array.from(document.querySelectorAll("#rows tr"));
                filter.addEventListener("input", function () {
                  const value = filter.value.toLowerCase();
                  for (const row of rows) {
                    row.style.display = row.textContent.toLowerCase().includes(value) ? "" : "none";
                  }
                });
              </script>
            </body>
            </html>
            """
        )
    )
    return template.safe_substitute(note_new_url=NOTE_NEW_TEXT_URL, rows="\n".join(rows))


def _issues_html(report: ArticleReport) -> str:
    if not report.issues:
        return "問題なし"
    items = [f"<li>{escape(issue.level)}: {escape(issue.message)}</li>" for issue in report.issues]
    return f"<ul class=\"issues\">{''.join(items)}</ul>"


def _auto_summary(body: str) -> str:
    text = " ".join(line.strip() for line in body.splitlines() if line.strip())
    return text[:120] + ("..." if len(text) > 120 else "")


def _markdown_preview(markdown: str) -> str:
    escaped = escape(markdown)
    if not escaped:
        return "<p></p>"
    return "<pre>" + escaped + "</pre>"

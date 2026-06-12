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
                  color-scheme: light dark;
                  --bg: #f3f5f9;
                  --bg-wash: radial-gradient(1200px 400px at 50% -10%, rgba(13,148,136,.07), transparent 60%);
                  --surface: #ffffff;
                  --surface-muted: #f7f9fc;
                  --border: rgba(15,23,42,.08);
                  --border-strong: rgba(15,23,42,.14);
                  --ink: #0f172a;
                  --muted: #64748b;
                  --accent: #0d9488;
                  --hover: #0f766e;
                  --soft: #ccfbf1;
                  --on-accent: #ffffff;
                  --danger: #dc2626;
                  --danger-soft: #fee2e2;
                  --warn: #b45309;
                  --warn-soft: #fef3c7;
                  --ok: #059669;
                  --ok-soft: #d1fae5;
                  --info: #2563eb;
                  --info-soft: #dbeafe;
                  --shadow-sm: 0 1px 2px rgba(15,23,42,.05);
                  --shadow-md: 0 1px 2px rgba(15,23,42,.05), 0 8px 24px -8px rgba(15,23,42,.12);
                  --radius-card: 16px;
                  --radius-control: 10px;
                  --radius-pill: 999px;
                  font-family: system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Yu Gothic UI", Meiryo, sans-serif;
                  background: var(--bg);
                  color: var(--ink);
                }
                @media (prefers-color-scheme: dark) {
                  :root {
                    --bg: #0b1220;
                    --bg-wash: radial-gradient(1200px 400px at 50% -10%, rgba(45,212,191,.06), transparent 60%);
                    --surface: #111a2c;
                    --surface-muted: #0e1626;
                    --border: rgba(148,163,184,.14);
                    --border-strong: rgba(148,163,184,.22);
                    --ink: #e2e8f0;
                    --muted: #94a3b8;
                    --accent: #2dd4bf;
                    --hover: #5eead4;
                    --soft: rgba(45,212,191,.14);
                    --on-accent: #042f2c;
                    --danger-soft: rgba(220,38,38,.18);
                    --warn-soft: rgba(180,83,9,.18);
                    --ok-soft: rgba(5,150,105,.18);
                    --info-soft: rgba(37,99,235,.18);
                    --shadow-sm: 0 1px 2px rgba(0,0,0,.24);
                    --shadow-md: 0 1px 2px rgba(0,0,0,.24), 0 12px 30px -12px rgba(0,0,0,.52);
                  }
                }
                * {
                  box-sizing: border-box;
                }
                body {
                  margin: 0;
                  min-height: 100vh;
                  padding: 28px;
                  background: var(--bg-wash), var(--bg);
                  color: var(--ink);
                  font: 15px/1.75 system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Yu Gothic UI", Meiryo, sans-serif;
                }
                main {
                  max-width: 1180px;
                  margin: 0 auto;
                }
                .topbar {
                  display: flex;
                  justify-content: space-between;
                  gap: 18px;
                  align-items: center;
                  margin-bottom: 18px;
                }
                .brand {
                  display: flex;
                  align-items: center;
                  gap: 11px;
                  min-width: 0;
                }
                .brand-mark {
                  align-items: center;
                  background: linear-gradient(135deg, #0d9488, #10b981);
                  border-radius: 9px;
                  box-shadow: var(--shadow-sm);
                  color: #ffffff;
                  display: inline-flex;
                  flex: 0 0 auto;
                  height: 28px;
                  justify-content: center;
                  width: 28px;
                }
                h1 {
                  margin: 0;
                  font-size: 20px;
                  font-weight: 700;
                  letter-spacing: -0.01em;
                  line-height: 1.2;
                }
                .brand small {
                  color: var(--muted);
                  display: block;
                  font-size: 12px;
                  line-height: 1.35;
                  margin-top: 2px;
                }
                .actions, .copy-row, .tabs {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 8px;
                  align-items: center;
                }
                a, button {
                  align-items: center;
                  border: 1px solid var(--border-strong);
                  border-radius: var(--radius-control);
                  color: var(--ink);
                  cursor: pointer;
                  display: inline-flex;
                  font: inherit;
                  font-weight: 650;
                  gap: 7px;
                  min-height: 38px;
                  padding: 8px 12px;
                  text-decoration: none;
                  transition: all .15s ease;
                  white-space: nowrap;
                }
                button {
                  background: transparent;
                }
                .primary,
                button.primary,
                a.primary {
                  background: linear-gradient(180deg, var(--accent), var(--hover));
                  border-color: transparent;
                  color: var(--on-accent);
                }
                .ghost,
                a.ghost {
                  background: transparent;
                }
                a:hover,
                button:hover {
                  background: var(--surface-muted);
                }
                .primary:hover,
                button.primary:hover,
                a.primary:hover {
                  background: linear-gradient(180deg, var(--hover), var(--accent));
                  box-shadow: var(--shadow-md);
                  transform: translateY(-1px);
                }
                a:active,
                button:active {
                  transform: scale(.98);
                }
                a:focus-visible,
                button:focus-visible,
                textarea:focus-visible,
                input:focus-visible {
                  outline: 2px solid color-mix(in srgb, var(--accent) 55%, transparent);
                  outline-offset: 2px;
                }
                .metrics {
                  display: grid;
                  grid-template-columns: repeat(4, minmax(120px, 1fr));
                  gap: 12px;
                  margin: 14px 0 18px;
                }
                .metric {
                  background: var(--surface);
                  border: 1px solid var(--border);
                  border-radius: var(--radius-card);
                  box-shadow: var(--shadow-sm);
                  overflow: hidden;
                  padding: 14px 15px 13px;
                  position: relative;
                }
                .metric::before {
                  background: var(--accent);
                  content: "";
                  height: 2px;
                  left: 0;
                  position: absolute;
                  right: 0;
                  top: 0;
                }
                .metric strong {
                  display: block;
                  font-size: 22px;
                  font-variant-numeric: tabular-nums;
                  font-weight: 700;
                  letter-spacing: 0;
                  line-height: 1.2;
                }
                .metric span {
                  color: var(--muted);
                  display: block;
                  font-size: 12px;
                  margin-top: 4px;
                }
                section, aside {
                  background: var(--surface);
                  border: 1px solid var(--border);
                  border-radius: var(--radius-card);
                  box-shadow: var(--shadow-sm);
                  margin-top: 14px;
                  overflow: hidden;
                  transition: all .15s ease;
                }
                section:focus-within,
                aside:focus-within {
                  border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
                  box-shadow: var(--shadow-md);
                }
                .bar {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  gap: 12px;
                  padding: 12px 14px 12px 16px;
                  border-bottom: 1px solid var(--border);
                  background: var(--surface-muted);
                }
                h2 {
                  font-size: 13.5px;
                  margin: 0;
                  font-weight: 650;
                  letter-spacing: 0;
                }
                .tabs {
                  background: var(--surface-muted);
                  border: 1px solid var(--border);
                  border-radius: var(--radius-pill);
                  gap: 2px;
                  padding: 3px;
                }
                .tabs button {
                  border: 0;
                  border-radius: var(--radius-pill);
                  min-height: 30px;
                  padding: 5px 11px;
                }
                .tabs button[data-tab="edit"] {
                  background: var(--surface);
                  box-shadow: var(--shadow-sm);
                }
                body:has(#preview.active) .tabs button[data-tab="edit"] {
                  background: transparent;
                  box-shadow: none;
                }
                body:has(#preview.active) .tabs button[data-tab="preview"] {
                  background: var(--surface);
                  box-shadow: var(--shadow-sm);
                }
                textarea, input {
                  display: block;
                  width: 100%;
                  border: 0;
                  background: var(--surface);
                  color: var(--ink);
                  resize: vertical;
                  padding: 16px;
                  font: 15px/1.65 ui-monospace, "Cascadia Code", Consolas, monospace;
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
                  color: var(--accent);
                  font-size: 13px;
                  min-height: 22px;
                  font-weight: 650;
                }
                .grid {
                  display: grid;
                  grid-template-columns: minmax(0, 1fr) 320px;
                  gap: 14px;
                  align-items: start;
                }
                .side {
                  padding: 16px;
                }
                .side dl {
                  margin: 0;
                }
                .side dt {
                  color: var(--muted);
                  font-size: 12px;
                  font-weight: 650;
                  margin-top: 12px;
                }
                .side dd {
                  margin: 4px 0 0;
                  overflow-wrap: anywhere;
                  font-size: 14px;
                }
                .side dd:first-of-type {
                  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
                }
                .issues {
                  margin: 8px 0 0;
                  padding: 0;
                  list-style: none;
                }
                .issues li {
                  align-items: flex-start;
                  display: flex;
                  gap: 8px;
                  margin: 7px 0;
                }
                .issues li::before {
                  background: var(--warn);
                  border-radius: 50%;
                  content: "";
                  flex: 0 0 auto;
                  height: 7px;
                  margin-top: .65em;
                  width: 7px;
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
                  background: #08111f;
                  border: 1px solid rgba(148,163,184,.22);
                  border-radius: 12px;
                  color: #e2e8f0;
                  overflow: auto;
                  padding: 14px;
                }
                svg {
                  flex: 0 0 auto;
                }
                @media (max-width: 860px) {
                  body {
                    padding: 16px;
                  }
                  .topbar, .bar {
                    align-items: flex-start;
                    flex-direction: column;
                  }
                  .grid {
                    grid-template-columns: 1fr;
                  }
                  .metrics {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                  }
                }
                @media (prefers-reduced-motion: reduce) {
                  *, *::before, *::after {
                    transition: none !important;
                  }
                }
              </style>
            </head>
            <body>
              <main>
                <header class="topbar">
                  <div class="brand">
                    <span class="brand-mark" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path>
                        <path d="M14 3v5h5"></path>
                        <path d="M9 15l2 2 4-6"></path>
                      </svg>
                    </span>
                    <div>
                      <h1>auto-note helper</h1>
                      <small>note投稿用コピー支援</small>
                    </div>
                  </div>
                  <div class="actions">
                    <a class="primary" href="$note_new_url" target="_blank" rel="noreferrer">note 投稿画面</a>
                    <a class="ghost" href="$note_login_url" target="_blank" rel="noreferrer">ログイン</a>
                  </div>
                </header>
                <div class="status" id="status"></div>

                <div class="metrics">
                  <div class="metric"><strong id="titleCount">$title_chars</strong><span>タイトル文字</span></div>
                  <div class="metric"><strong id="bodyCount">$body_chars</strong><span>本文文字</span></div>
                  <div class="metric"><strong id="lineCount">$lines</strong><span>行</span></div>
                  <div class="metric"><strong id="readTime">$reading_minutes</strong><span>分目安</span></div>
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
    article_count = len(items)
    ok_count = sum(1 for item in items if item.report.ok)
    ng_count = article_count - ok_count
    scheduled_count = sum(1 for item in items if item.report.article.scheduled)
    rows = []
    for item in items:
        report = item.report
        article = report.article
        status = "OK" if report.ok else "NG"
        issue_count = len(report.issues)
        tags = "".join(f"<span class=\"tag\">{escape(tag)}</span>" for tag in article.tags)
        scheduled = escape(article.scheduled) if article.scheduled else "<span class=\"muted-dash\">—</span>"
        issues = str(issue_count) if issue_count else "<span class=\"muted-dash\">—</span>"
        rows.append(
            "<tr>"
            f"<td><span class=\"badge {status.lower()}\">{status}</span></td>"
            f"<td class=\"article-cell\"><a href=\"{escape(item.helper_path.resolve().as_uri())}\">{escape(article.title)}</a>"
            f"<small>{escape(str(article.source))}</small></td>"
            f"<td>{escape(article.status)}</td>"
            f"<td>{scheduled}</td>"
            f"<td class=\"num\">{report.stats.body_chars}</td>"
            f"<td class=\"num\">{report.stats.reading_minutes}</td>"
            f"<td><div class=\"tags\">{tags or '<span class=\"muted-dash\">—</span>'}</div></td>"
            f"<td class=\"num\">{issues}</td>"
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
                  color-scheme: light dark;
                  --bg: #f3f5f9;
                  --bg-wash: radial-gradient(1200px 400px at 50% -10%, rgba(13,148,136,.07), transparent 60%);
                  --surface: #ffffff;
                  --surface-muted: #f7f9fc;
                  --border: rgba(15,23,42,.08);
                  --border-strong: rgba(15,23,42,.14);
                  --ink: #0f172a;
                  --muted: #64748b;
                  --accent: #0d9488;
                  --hover: #0f766e;
                  --soft: #ccfbf1;
                  --on-accent: #ffffff;
                  --danger: #dc2626;
                  --danger-soft: #fee2e2;
                  --warn: #b45309;
                  --warn-soft: #fef3c7;
                  --ok: #059669;
                  --ok-soft: #d1fae5;
                  --info: #2563eb;
                  --info-soft: #dbeafe;
                  --shadow-sm: 0 1px 2px rgba(15,23,42,.05);
                  --shadow-md: 0 1px 2px rgba(15,23,42,.05), 0 8px 24px -8px rgba(15,23,42,.12);
                  --radius-card: 16px;
                  --radius-control: 10px;
                  --radius-pill: 999px;
                  font-family: system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Yu Gothic UI", Meiryo, sans-serif;
                  background: var(--bg);
                  color: var(--ink);
                }
                @media (prefers-color-scheme: dark) {
                  :root {
                    --bg: #0b1220;
                    --bg-wash: radial-gradient(1200px 400px at 50% -10%, rgba(45,212,191,.06), transparent 60%);
                    --surface: #111a2c;
                    --surface-muted: #0e1626;
                    --border: rgba(148,163,184,.14);
                    --border-strong: rgba(148,163,184,.22);
                    --ink: #e2e8f0;
                    --muted: #94a3b8;
                    --accent: #2dd4bf;
                    --hover: #5eead4;
                    --soft: rgba(45,212,191,.14);
                    --on-accent: #042f2c;
                    --danger-soft: rgba(220,38,38,.18);
                    --warn-soft: rgba(180,83,9,.18);
                    --ok-soft: rgba(5,150,105,.18);
                    --info-soft: rgba(37,99,235,.18);
                    --shadow-sm: 0 1px 2px rgba(0,0,0,.24);
                    --shadow-md: 0 1px 2px rgba(0,0,0,.24), 0 12px 30px -12px rgba(0,0,0,.52);
                  }
                }
                * {
                  box-sizing: border-box;
                }
                body {
                  margin: 0;
                  min-height: 100vh;
                  padding: 28px;
                  background: var(--bg-wash), var(--bg);
                  color: var(--ink);
                  font: 15px/1.75 system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Yu Gothic UI", Meiryo, sans-serif;
                }
                main {
                  max-width: 1180px;
                  margin: 0 auto;
                }
                .topbar {
                  display: flex;
                  justify-content: space-between;
                  gap: 18px;
                  align-items: center;
                  margin-bottom: 18px;
                }
                .brand {
                  display: flex;
                  align-items: center;
                  gap: 11px;
                  min-width: 0;
                }
                .brand-mark {
                  align-items: center;
                  background: linear-gradient(135deg, #0d9488, #10b981);
                  border-radius: 9px;
                  box-shadow: var(--shadow-sm);
                  color: #ffffff;
                  display: inline-flex;
                  flex: 0 0 auto;
                  height: 28px;
                  justify-content: center;
                  width: 28px;
                }
                h1 {
                  margin: 0;
                  font-size: 20px;
                  font-weight: 700;
                  letter-spacing: -0.01em;
                  line-height: 1.2;
                }
                .brand small {
                  color: var(--muted);
                  display: block;
                  font-size: 12px;
                  line-height: 1.35;
                  margin-top: 2px;
                }
                a {
                  align-items: center;
                  border: 1px solid var(--border-strong);
                  border-radius: var(--radius-control);
                  color: var(--ink);
                  display: inline-flex;
                  font: inherit;
                  font-weight: 650;
                  gap: 7px;
                  min-height: 38px;
                  padding: 8px 12px;
                  text-decoration: none;
                  transition: all .15s ease;
                  white-space: nowrap;
                }
                a.primary {
                  background: linear-gradient(180deg, var(--accent), var(--hover));
                  border-color: transparent;
                  color: var(--on-accent);
                }
                a:hover {
                  background: var(--surface-muted);
                }
                a.primary:hover {
                  background: linear-gradient(180deg, var(--hover), var(--accent));
                  box-shadow: var(--shadow-md);
                  transform: translateY(-1px);
                }
                a:active {
                  transform: scale(.98);
                }
                a:focus-visible,
                input:focus-visible {
                  outline: 2px solid color-mix(in srgb, var(--accent) 55%, transparent);
                  outline-offset: 2px;
                }
                .stats {
                  display: grid;
                  grid-template-columns: repeat(4, minmax(0, 1fr));
                  gap: 12px;
                  margin: 0 0 16px;
                }
                .stat {
                  background: var(--surface);
                  border: 1px solid var(--border);
                  border-radius: var(--radius-card);
                  box-shadow: var(--shadow-sm);
                  padding: 14px 15px;
                }
                .stat strong {
                  display: block;
                  font-size: 24px;
                  font-variant-numeric: tabular-nums;
                  font-weight: 700;
                  letter-spacing: 0;
                  line-height: 1.15;
                }
                .stat span {
                  color: var(--muted);
                  display: block;
                  font-size: 12px;
                  font-weight: 650;
                  margin-top: 4px;
                }
                .search-row {
                  align-items: center;
                  display: grid;
                  gap: 10px;
                  grid-template-columns: minmax(0, 1fr) auto;
                  margin-bottom: 12px;
                }
                .search {
                  position: relative;
                }
                .search svg {
                  color: var(--muted);
                  left: 14px;
                  position: absolute;
                  top: 50%;
                  transform: translateY(-50%);
                }
                input {
                  width: 100%;
                  border: 1px solid var(--border-strong);
                  border-radius: var(--radius-control);
                  background: var(--surface);
                  color: var(--ink);
                  padding: 11px 14px 11px 42px;
                  font: inherit;
                  transition: all .15s ease;
                }
                .filter-count {
                  color: var(--muted);
                  font-size: 12px;
                  font-variant-numeric: tabular-nums;
                  font-weight: 650;
                  white-space: nowrap;
                }
                .table-card {
                  background: var(--surface);
                  border: 1px solid var(--border);
                  border-radius: var(--radius-card);
                  box-shadow: var(--shadow-sm);
                  overflow: hidden;
                }
                .table-scroll {
                  overflow-x: auto;
                }
                table {
                  width: 100%;
                  min-width: 900px;
                  border-collapse: separate;
                  border-spacing: 0;
                }
                th, td {
                  padding: 12px 14px;
                  border-bottom: 1px solid var(--border);
                  text-align: left;
                  vertical-align: top;
                }
                th {
                  background: var(--surface-muted);
                  color: var(--muted);
                  font-size: 11px;
                  font-weight: 700;
                  letter-spacing: .08em;
                  position: sticky;
                  text-transform: uppercase;
                  top: 0;
                  z-index: 1;
                }
                tbody tr {
                  transition: background-color .15s ease;
                }
                tbody tr:hover {
                  background: var(--surface-muted);
                }
                tbody tr:last-child td {
                  border-bottom: 0;
                }
                small {
                  display: block;
                  color: var(--muted);
                  font-size: 12px;
                  line-height: 1.45;
                  margin-top: 4px;
                  overflow-wrap: anywhere;
                }
                .article-cell a {
                  border: 0;
                  color: var(--ink);
                  display: inline;
                  font-weight: 600;
                  min-height: 0;
                  padding: 0;
                  text-decoration: none;
                  white-space: normal;
                }
                .article-cell a:hover {
                  color: var(--accent);
                  background: transparent;
                }
                .badge {
                  align-items: center;
                  border-radius: var(--radius-pill);
                  display: inline-flex;
                  gap: 6px;
                  font-size: 12px;
                  font-variant-numeric: tabular-nums;
                  font-weight: 650;
                  min-width: 48px;
                  padding: 3px 9px;
                }
                .badge::before {
                  border-radius: 50%;
                  content: "";
                  height: 7px;
                  width: 7px;
                }
                .ok {
                  background: var(--ok-soft);
                  color: var(--ok);
                }
                .ok::before {
                  background: var(--ok);
                }
                .ng {
                  background: var(--danger-soft);
                  color: var(--danger);
                }
                .ng::before {
                  background: var(--danger);
                }
                .tags {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 5px;
                }
                .tag {
                  background: var(--soft);
                  border-radius: var(--radius-pill);
                  color: var(--accent);
                  display: inline-flex;
                  font-size: 12px;
                  line-height: 1.4;
                  padding: 2px 8px;
                }
                .num {
                  font-variant-numeric: tabular-nums;
                }
                .muted-dash {
                  color: var(--muted);
                }
                @media (max-width: 760px) {
                  body {
                    padding: 16px;
                  }
                  .topbar {
                    flex-direction: column;
                    align-items: flex-start;
                  }
                  .stats {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                  }
                  .search-row {
                    grid-template-columns: 1fr;
                  }
                }
                @media (prefers-reduced-motion: reduce) {
                  *, *::before, *::after {
                    transition: none !important;
                  }
                }
              </style>
            </head>
            <body>
              <main>
                <header class="topbar">
                  <div class="brand">
                    <span class="brand-mark" aria-hidden="true">
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"></path>
                        <path d="M14 3v5h5"></path>
                        <path d="M9 15l2 2 4-6"></path>
                      </svg>
                    </span>
                    <div>
                      <h1>auto-note</h1>
                      <small>dashboard</small>
                    </div>
                  </div>
                  <a class="primary" href="$note_new_url" target="_blank" rel="noreferrer">
                    note 投稿画面
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                      <path d="M15 3h6v6"></path>
                      <path d="M10 14L21 3"></path>
                    </svg>
                  </a>
                </header>
                <div class="stats">
                  <div class="stat"><strong>$article_count</strong><span>記事数</span></div>
                  <div class="stat"><strong>$ok_count</strong><span>OK</span></div>
                  <div class="stat"><strong>$ng_count</strong><span>NG</span></div>
                  <div class="stat"><strong>$scheduled_count</strong><span>予定あり</span></div>
                </div>
                <div class="search-row">
                  <div class="search">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <circle cx="11" cy="11" r="8"></circle>
                      <path d="M21 21l-4.35-4.35"></path>
                    </svg>
                    <input id="filter" placeholder="検索">
                  </div>
                  <div class="filter-count" id="resultCount">$article_count件</div>
                </div>
                <div class="table-card">
                  <div class="table-scroll">
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
                  </div>
                </div>
              </main>
              <script>
                const filter = document.getElementById("filter");
                const rows = Array.from(document.querySelectorAll("#rows tr"));
                const resultCount = document.getElementById("resultCount");
                function updateFilter() {
                  const value = filter.value.toLowerCase();
                  let visible = 0;
                  for (const row of rows) {
                    const matched = row.textContent.toLowerCase().includes(value);
                    row.style.display = matched ? "" : "none";
                    if (matched) {
                      visible += 1;
                    }
                  }
                  resultCount.textContent = visible + " / " + rows.length + "件";
                }
                filter.addEventListener("input", updateFilter);
                updateFilter();
              </script>
            </body>
            </html>
            """
        )
    )
    return template.safe_substitute(
        note_new_url=NOTE_NEW_TEXT_URL,
        rows="\n".join(rows),
        article_count=str(article_count),
        ok_count=str(ok_count),
        ng_count=str(ng_count),
        scheduled_count=str(scheduled_count),
    )


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

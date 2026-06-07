from __future__ import annotations


def write_clipboard(text: str) -> None:
    try:
        import tkinter
    except ModuleNotFoundError as exc:
        raise RuntimeError("この環境ではクリップボード機能を使えません。") from exc

    root = tkinter.Tk()
    root.withdraw()
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
    finally:
        root.destroy()

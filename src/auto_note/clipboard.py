from __future__ import annotations


def write_clipboard(text: str) -> None:
    try:
        import tkinter
    except ModuleNotFoundError as exc:
        raise RuntimeError("この環境ではクリップボード機能を使えません。") from exc

    root = None
    try:
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
    except tkinter.TclError as exc:
        raise RuntimeError("この環境ではクリップボード機能を使えません。") from exc
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass

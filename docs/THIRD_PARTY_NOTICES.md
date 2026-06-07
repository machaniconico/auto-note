# Third-party Notices

auto-note uses the Python packages below. Confirm the installed versions before each commercial release with:

```powershell
$env:PYTHONPATH='src'; python -m auto_note licenses
```

## Required dependency

- `PyYAML`: Reads article frontmatter metadata.

## Optional dependencies

- `Pillow`: Resizes and compresses imported images when image optimization is enabled.
- `playwright`: Drives a browser for environments where automated posting is usable.

## Optional transitive dependencies

These can be installed by optional features such as Playwright:

- `pyee`
- `greenlet`
- `typing-extensions`

## Release notes

- The release ZIP excludes `.venv`, so third-party package files are not bundled in the source distribution.
- If the distribution method changes to bundle Python, `.venv`, a standalone executable, or embedded browser binaries, review third-party license obligations again.
- Review dependency versions and license metadata when updating `pyproject.toml`.

# /// script
# dependencies = ["mcp"]
# ///
"""MCP-сервер чтения кода 1С — точный контекст по РЕАЛЬНОМУ коду, чтобы AI не гадал.

Поверх локальных клонов конфигураций/расширений 1С (EDT- или Designer-XML формат), поиск через ripgrep
(с чистым Python-фолбэком). АВТО-ПОДХВАТ всех репозиториев в каталоге исходников: склонировал репо в
ONEC_SRC_DIR — search/find/read видят его без правок. Каждый слой тегируется именем своего репозитория [repo].

Запуск: uv run erp_mcp.py   (или python erp_mcp.py)
Каталог исходников: переменная окружения ONEC_SRC_DIR (по умолчанию ~/erp-src). Кроссплатформенно.
"""
import os, glob, re, shutil, subprocess
from mcp.server.fastmcp import FastMCP

# Транспорт: stdio (локально, по умолчанию) или http/sse (контейнер/центральный сервис).
# Управляется env MCP_TRANSPORT (stdio|sse|streamable-http), MCP_HOST, MCP_PORT.
mcp = FastMCP("erp-1c",
              host=os.environ.get("MCP_HOST", "0.0.0.0"),
              port=int(os.environ.get("MCP_PORT", "8000")))
HOME = os.path.expanduser("~")
SRC = (os.environ.get("ONEC_SRC_DIR") or os.path.join(HOME, "erp-src")).replace("\\", "/")
# Репозитории-исключения (тестовые песочницы и т.п.) — не подхватывать.
IGNORE = {r.strip() for r in os.environ.get("ONEC_SRC_IGNORE", "sandbox").split(",") if r.strip()}


def _repo_of(path):
    return os.path.relpath(path, SRC).replace("\\", "/").split("/")[0]


def _discover_roots():
    """Найти корни конфигураций/расширений в SRC по подпапке CommonModules.
    Оба layout: EDT `<repo>/src/<имя>/src` и Designer-XML `<repo>/src/<имя>`.
    Вызывается ОДИН РАЗ при старте — новые клоны видны после перезапуска."""
    roots, seen = [], set()
    for pat in (f"{SRC}/*/src/*/src", f"{SRC}/*/src/*", f"{SRC}/*/src", f"{SRC}/*"):
        for p in sorted(glob.glob(pat)):
            p = p.replace("\\", "/")
            if p in seen or not os.path.isdir(p):
                continue
            if _repo_of(p) in IGNORE:
                continue
            if os.path.isdir(os.path.join(p, "CommonModules")):
                roots.append(p)
                seen.add(p)
    # длинные пути первыми — корректная замена корня на тег в выводе
    return sorted(roots, key=len, reverse=True)


_ROOTS = _discover_roots()
_ROOT_TAGS = [(r, f"[{_repo_of(r)}]") for r in _ROOTS]


def _retag(text):
    for root, tag in _ROOT_TAGS:
        text = text.replace(root, tag)
    return text


def _find_rg():
    exe = shutil.which("rg")
    if exe:
        return exe
    for c in (r"C:\Program Files\ripgrep\rg.exe",
              os.path.join(HOME, ".local", "bin", "rg.exe"),
              os.path.join(HOME, "scoop", "shims", "rg.exe")):
        if os.path.isfile(c):
            return c
    for c in glob.glob(os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet",
                                    "Packages", "BurntSushi.ripgrep*", "**", "rg.exe"), recursive=True):
        if os.path.isfile(c):
            return c
    return None


RG = _find_rg()


def _grep(query, dirs, timeout=180):
    if RG:
        try:
            r = subprocess.run([RG, "-n", "--no-heading", "-i", "-S", "--path-separator", "/", query, *dirs],
                               capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            return r.stdout.splitlines()
        except Exception as e:
            return [f"[ошибка поиска rg: {e}]"]
    ql, out = query.lower(), []
    for base in dirs:
        for root, _, files in os.walk(base):
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    if os.path.getsize(fp) > 4_000_000:
                        continue
                    with open(fp, encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if ql in line.lower():
                                out.append(f"{fp.replace(chr(92), '/')}:{i}:{line.rstrip()}")
                                if len(out) >= 5000:
                                    return out
                except Exception:
                    pass
    return out


@mcp.tool()
def search_1c(query: str, max_results: int = 40) -> str:
    """Поиск по РЕАЛЬНОМУ коду 1С во всех склонированных конфигурациях/расширениях.
    Используй, чтобы проверить, как устроена типовая или есть ли уже готовое в расширении, а не гадать.
    query — текст/имя метода/объекта (регистр игнорируется)."""
    if not _ROOTS:
        return f"код не найден локально ({SRC}). Склонируй репозитории в ONEC_SRC_DIR."
    raw = _grep(query, _ROOTS)
    if not raw:
        return f"по '{query}' ничего не найдено."
    head = [_retag(l) for l in raw[:max_results]]
    extra = len(raw) - max_results
    return "\n".join(head) + (f"\n... ещё {extra} совпадений" if extra > 0 else "")


@mcp.tool()
def find_object(name: str) -> str:
    """Найти объект метаданных (Документ, Справочник, Регистр, ОбщийМодуль, Перечисление и т.п.) по имени
    или части имени. Возвращает пути в каждом слое (тег [repo])."""
    if not _ROOTS:
        return f"код не найден локально ({SRC})."
    found, nl = [], name.lower()
    for base in _ROOTS:
        base_depth = base.rstrip("/").count("/")
        for root, dnames, _ in os.walk(base):
            if root.replace("\\", "/").rstrip("/").count("/") - base_depth >= 3:
                dnames[:] = []
            for d in dnames:
                if nl in d.lower():
                    found.append(f"[{_repo_of(base)}] {os.path.relpath(os.path.join(root, d), base)}")
    return "\n".join(sorted(set(found))[:60]) or f"объект '{name}' не найден."


@mcp.tool()
def read_module(path: str, start: int = 1, end: int = 250) -> str:
    """Прочитать BSL-модуль или метаданные по пути (как из search_1c/find_object), строки start..end.
    Путь можно дать относительно тега [repo] или абсолютный."""
    p = path.strip()
    for root, tag in _ROOT_TAGS:
        p = p.replace(tag, root)
    p = p.strip()
    if not os.path.isabs(p):
        for base in _ROOTS:
            cand = os.path.join(base, p)
            if os.path.exists(cand):
                p = cand
                break
    if not os.path.isfile(p):
        return f"файл не найден: {path}"
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        chunk = lines[max(0, start - 1):end]
        return f"{os.path.basename(p)} (строки {start}-{min(end, len(lines))} из {len(lines)}):\n" + "".join(chunk)
    except Exception as e:
        return f"ошибка чтения: {e}"


@mcp.tool()
def list_modules() -> str:
    """Список общих модулей по всем слоям — что уже реализовано, чтобы переиспользовать, а не изобретать."""
    blocks = []
    for root in _ROOTS:
        d = os.path.join(root, "CommonModules")
        if not os.path.isdir(d):
            continue
        mods = sorted(os.listdir(d))
        blocks.append(f"Общие модули — [{_repo_of(root)}]:\n" + "\n".join(f"- {m}" for m in mods))
    return "\n\n".join(blocks) if blocks else "модули не найдены."


if __name__ == "__main__":
    # stdio для локального Claude Code; sse/streamable-http — для запуска в Docker как центрального сервиса.
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))

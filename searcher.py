import os
import threading
from pathlib import Path


def get_search_roots():
    """Get common directories to search."""
    roots = []
    home = Path.home()
    roots.append(home / "Desktop")
    roots.append(home / "Documents")
    roots.append(home / "Downloads")

    public_desktop = Path("C:/Users/Public/Desktop")
    if public_desktop.exists():
        roots.append(public_desktop)

    return [str(r) for r in roots if r.exists()]


def fuzzy_match(query, name):
    query = query.lower()
    name_lower = name.lower()
    if query in name_lower:
        return True
    qi = 0
    for ch in name_lower:
        if qi < len(query) and ch == query[qi]:
            qi += 1
    return qi == len(query)


def search_files(query, callback, max_results=50):
    """Search files by walking common directories. Calls callback with results list."""
    if not query or len(query) < 2:
        callback([])
        return

    def run():
        results = []
        roots = get_search_roots()

        for root_dir in roots:
            try:
                for dirpath, dirnames, filenames in os.walk(root_dir):
                    # skip hidden and system folders
                    dirnames[:] = [d for d in dirnames if not d.startswith('.')]

                    for name in filenames + dirnames:
                        if fuzzy_match(query, name):
                            full_path = os.path.join(dirpath, name)
                            results.append(full_path)
                            if len(results) >= max_results:
                                callback(results)
                                return

                    # limit depth to avoid long searches
                    depth = dirpath.replace(root_dir, "").count(os.sep)
                    if depth >= 4:
                        dirnames.clear()
            except PermissionError:
                continue

        callback(results)

    t = threading.Thread(target=run, daemon=True)
    t.start()


def search_desktop_only(query):
    """Synchronous search on desktop only, returns list of filenames."""
    results = []
    home = Path.home()
    desktop = home / "Desktop"

    if desktop.exists():
        try:
            for item in os.listdir(desktop):
                if fuzzy_match(query, item):
                    results.append(item)
        except Exception:
            pass

    public_desktop = Path("C:/Users/Public/Desktop")
    if public_desktop.exists():
        try:
            for item in os.listdir(public_desktop):
                if fuzzy_match(query, item) and item not in results:
                    results.append(item)
        except Exception:
            pass

    return results


def open_in_explorer(filepath):
    """Open Explorer with the file selected."""
    import subprocess
    filepath = os.path.normpath(filepath)
    if os.path.exists(filepath):
        subprocess.Popen(f'explorer /select,"{filepath}"')


if __name__ == "__main__":
    import time
    results = []
    def cb(r): results.extend(r)
    search_files("chrome", cb)
    time.sleep(3)
    print(f"Found {len(results)} results:")
    for p in results[:10]:
        print(f"  exists={os.path.exists(p)}  {p}")

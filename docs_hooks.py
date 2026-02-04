"""MkDocs hooks: copy sitemap into language subdirs so /ru/sitemap.xml works (avoids 404 in dev and for crawlers)."""

import os
import shutil


def on_post_build(config, **kwargs):
    site_dir = config["site_dir"]
    for name in ("sitemap.xml", "sitemap.xml.gz"):
        src = os.path.join(site_dir, name)
        if not os.path.isfile(src):
            continue
        ru_dir = os.path.join(site_dir, "ru")
        if os.path.isdir(ru_dir):
            shutil.copy2(src, os.path.join(ru_dir, name))

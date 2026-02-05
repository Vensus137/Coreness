"""MkDocs hooks: copy sitemap, fix SEO issues."""

import os
import shutil
import re
from pathlib import Path


def on_post_build(config, **kwargs):
    """Post-build hook: sitemap and fix external links."""
    site_dir = config["site_dir"]
    config_dir = os.path.dirname(os.path.abspath(__file__))
    site_dir_abs = os.path.normpath(os.path.join(config_dir, site_dir))

    # Copy sitemap into language subdirs
    for name in ("sitemap.xml", "sitemap.xml.gz"):
        src = os.path.join(site_dir_abs, name)
        if not os.path.isfile(src):
            continue
        for lang in ("ru", "en"):
            lang_dir = os.path.join(site_dir_abs, lang)
            if os.path.isdir(lang_dir):
                shutil.copy2(src, os.path.join(lang_dir, name))

    fix_html_files(site_dir_abs)


def fix_html_files(site_dir):
    """Fix external links security attributes and add image dimensions."""
    for html_file in Path(site_dir).rglob("*.html"):
        if html_file.name == "404.html":
            continue
            
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified = False
            
            # Fix external links without rel="noopener noreferrer"
            # Match links that have target="_blank" or are external
            def fix_external_link(match):
                link = match.group(0)
                # Skip if already has noopener
                if 'rel=' in link and 'noopener' in link:
                    return link
                # Add or update rel attribute
                if 'rel="' in link:
                    link = re.sub(r'rel="([^"]*)"', r'rel="\1 noopener noreferrer"', link)
                else:
                    link = link.replace('>', ' rel="noopener noreferrer">', 1)
                return link
            
            # Find external links (https://) and those with target="_blank"
            new_content = re.sub(
                r'<a\s+[^>]*(?:href="https?://(?!coreness\.tech)[^"]*"|target="_blank")[^>]*>',
                fix_external_link,
                content
            )
            
            if new_content != content:
                modified = True
                content = new_content
            
            # Add dimensions to badge images (common pattern)
            # This is a simple fix for shield.io badges
            badge_pattern = r'<img\s+([^>]*)src="https://img\.shields\.io/[^"]*"([^>]*)>'
            
            def add_badge_dimensions(match):
                attrs_before = match.group(1)
                attrs_after = match.group(2)
                # Check if width/height already exist
                if 'width=' not in attrs_before + attrs_after and 'height=' not in attrs_before + attrs_after:
                    return f'<img {attrs_before}src="https://img.shields.io/{match.group(0).split("/")[-1].split(">")[0]}" width="120" height="20"{attrs_after}>'
                return match.group(0)
            
            new_content = re.sub(badge_pattern, add_badge_dimensions, content)
            
            if new_content != content:
                modified = True
                content = new_content
            
            # Write back if modified
            if modified:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        except Exception as e:
            print(f"Warning: Could not process {html_file}: {e}")

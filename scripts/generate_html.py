import re
import html
import base64
import os
import argparse
import markdown

def encode_images_in_md(md_content, base_dir):
    def resolve(img_path):
        if img_path.startswith(('http://', 'https://', 'data:')):
            return None
        abs_path = img_path if img_path.startswith('/') else os.path.join(base_dir, img_path)
        if not os.path.exists(abs_path):
            return None
        with open(abs_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(abs_path)[1][1:].lower()
        if ext == 'jpg':
            ext = 'jpeg'
        return f'data:image/{ext};base64,{encoded}'

    def replace_image(match):
        alt_text = match.group(1)
        data_uri = resolve(match.group(2))
        if data_uri:
            return f'![{alt_text}]({data_uri})'
        return match.group(0)

    # 1) Markdown image syntax: ![alt](path)
    md_content = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', replace_image, md_content)

    # 2) Raw HTML <img src="path"> (used by hand-written <figure> blocks)
    def replace_img_tag(match):
        quote, img_path = match.group(1), match.group(2)
        data_uri = resolve(img_path)
        if data_uri:
            return f'src={quote}{data_uri}{quote}'
        return match.group(0)

    md_content = re.sub(r'src=(["\'])([^"\']+)\1', replace_img_tag, md_content)
    return md_content

def main():
    parser = argparse.ArgumentParser(description="Convert MD to HTML for group meeting paper reading.")
    parser.add_argument("md_file", help="Path to the markdown file")
    args = parser.parse_args()

    md_file = args.md_file
    out_file = os.path.splitext(md_file)[0] + ".html"
    
    # Path to the template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_template = os.path.join(script_dir, "..", "assets", "template.html")

    if not os.path.exists(md_file):
        print(f"Error: Could not find {md_file}")
        return
        
    with open(md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    md_dir = os.path.dirname(os.path.abspath(md_file))
    md_content = encode_images_in_md(md_content, md_dir)

    # Strip YAML frontmatter before conversion so that title/subtitle/date
    # do not leak into the rendered body as stray paragraphs.
    frontmatter = ""
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', md_content, re.S)
    if fm_match:
        frontmatter = fm_match.group(1)
        md_content = md_content[fm_match.end():]

    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'md_in_html'])
    html_body = md.convert(md_content)
    toc_html = md.toc

    # Title/subtitle/date come from frontmatter first, then from the body.
    title_source = frontmatter if frontmatter else md_content

    with open(html_template, "r", encoding="utf-8") as f:
        template = f.read()

    # Get the title from YAML frontmatter or markdown
    actual_title = None
    yaml_title = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', title_source, re.M)
    if yaml_title:
        actual_title = yaml_title.group(1).strip()
    else:
        title_match = re.search(r'^#\s+(.*)', md_content, re.M)
        if title_match:
            actual_title = title_match.group(1).strip()
    
    if not actual_title:
        actual_title = "组会文献解读"

    short_title = actual_title.split("：")[0].split(":")[0].strip()
    template = template.replace('【论文完整标题】', actual_title)
    template = template.replace('【论文短标题】', short_title)

    # Subtitle and Date
    yaml_sub = re.search(r'^subtitle:\s*["\']?(.*?)["\']?\s*$', title_source, re.M)
    yaml_date = re.search(r'^date:\s*["\']?(.*?)["\']?\s*$', title_source, re.M)
    sub_text = yaml_sub.group(1).strip() if yaml_sub else "组会文献解读"
    date_text = yaml_date.group(1).strip() if yaml_date else ""

    if date_text:
        template = template.replace('日期：____', f'日期：{date_text}')
    if yaml_sub:
        template = template.replace('组会文献解读 · 汇报人：____', f'{sub_text} · 汇报人：____')

    # Model signature: only what the frontmatter records; never guessed here.
    def field(name):
        m = re.search(rf'^{name}:[ \t]*["\']?(.*?)["\']?[ \t]*$', frontmatter, re.M)
        return m.group(1).strip() if m else ""

    model = field("model")
    signature = f"解读模型：{model or '未记录'}"
    if field("model_effort"):
        signature += f" · 推理强度：{field('model_effort')}"
    if field("model_note"):
        signature += f" · {field('model_note')}"
    if date_text and model:
        signature += f" · {date_text}"
    if not model:
        print("Warning: frontmatter has no `model:`; signature shows 未记录")
    template = template.replace("<!-- SIGNATURE -->", html.escape(signature))

    # Inject into placeholders
    final_html = template.replace("<!-- NAV -->", toc_html)
    final_html = final_html.replace("<!-- CONTENT -->", html_body)

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"Successfully generated {out_file}")

if __name__ == "__main__":
    main()

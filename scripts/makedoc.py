import re
import argparse

import markdown2
from bs4 import BeautifulSoup

# rewrite a template using the rewrite_map (tag -> output)
# replace all "{{key}}" in the template with rewrite_map["key"]
def template_rewrite(template, rewrite_map):
    output = []
    remaining_template = template
    res = re.search("\{\{([a-zA-Z0-9]+)\}\}", remaining_template)
    while res is not None:
        # print(res)
        tag = res.group(1) # tag word, not including curly bracket
        span = res.span(0) # span of the entire thing (include curly bracket)
        output.append(remaining_template[:span[0]])
        if tag in rewrite_map:
            output.append(rewrite_map[tag])
        else:
            output.append(res.group(0))
            raise RuntimeError(f"'{tag}' not found in rewrite map")
        remaining_template = remaining_template[span[1]:]
        res = re.search("\{\{([a-zA-Z0-9]+)\}\}", remaining_template)
    output.append(remaining_template)
    return "".join(output)

def makedoc(mdfile, outputfile, templatefile=None):
    # mdfile = "r1/summary.md"
    with open(mdfile, "r") as f:
        md = f.read()

    html = markdown2.markdown(md)
    if templatefile is not None:
        # templatefile = "template.html"
        with open(templatefile, "r") as f:
            template = f.read()
        # find title first (content of first <h1>)
        res = re.search('<h1>(.*?)</h1>', html)
        title = res.group(1) if res is not None else "NO_TITLE"
        html = template_rewrite(template, { 'title': title, 'content': html })

    soup = BeautifulSoup(html, "html.parser")

    # For all img tag, change their parent from <p> to <div>
    imgs = soup.find_all("img")
    for x in imgs:
        x.parent.name = "div"
        x.parent["class"] = "img"

    # outputfile = "r1/summary.html"
    with open(outputfile, "w") as f:
        f.write(soup.prettify())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="makedoc")
    parser.add_argument("input", help="input markdown file")
    parser.add_argument("output", help="output html file")
    parser.add_argument("-t", "--template", help="template html file")

    args = parser.parse_args()
    makedoc(args.input, args.output, templatefile=args.template)

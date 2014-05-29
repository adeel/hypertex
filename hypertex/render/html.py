__name__ = "html"

import os.path
import codecs
import tempfile
import subprocess
import hashlib
from jinja2 import Environment, PackageLoader
import wand.image, wand.color

from hypertex.parser import parse_tag, get_number_of_par
from hypertex.constants import BLOCK_TAGS
from hypertex.util import dict_merge

temp_env = Environment(loader=PackageLoader("hypertex.render", "html"))

def _render_content(node, parsed, imgs):
  if type(node) in (str, unicode):
    return node
  content = node.get("content", "")
  if type(content) is list:
    c = ""
    for n in content:
      r = _render_node(n, parsed, imgs)
      c += r["content"]
      imgs = r["imgs"]
    content = c
  return {"content": content, "imgs": imgs}

def _render_citation(node, parsed, imgs):
  tag = node.get("tag", "")
  ref = node.get("ref", "")
  url = ""
  num = 0
  doc = ""
  r = _render_content(node, parsed, imgs)
  text = r["content"]
  if tag:
    (doc, partag) = parse_tag(tag)
    num = get_number_of_par(partag, doc, parsed)
    url = "#"
    if doc:
      url = "%s.html#%d" % (doc, num)
    else:
      url = "#%d" % num
  elif ref:
    # TODO
    url = "#%s" % ref

  template = temp_env.get_template("citation.html")
  content = template.render({
    "tag":  tag,
    "doc":  doc,
    "num":  str(num),
    "ref":  ref,
    "url":  url,
    "text": text})
  return {"content": content, "imgs": imgs}

def _render_term(node, parsed, imgs):
  tag = node.get("tag", "")
  ref = node.get("ref", "")
  url = ""
  num = 0
  doc = ""
  r = _render_content(node, parsed, imgs)
  text = r["content"]
  if tag:
    (doc, partag) = parse_tag(tag)
    num = get_number_of_par(partag, doc, parsed)
    url = "#"
    if doc:
      url = "%s.html#%d" % (doc, num)
    else:
      url = "#%d" % num
  elif ref:
    # TODO
    url = "#%s" % ref

  template = temp_env.get_template("term.html")
  content = template.render({
    "tag":  tag,
    "doc":  doc,
    "num":  str(num),
    "ref":  ref,
    "url":  url,
    "text": text})
  return {"content": content, "imgs": imgs}

def _compile_formula_to_pdf(formula):
  "Takes a LaTeX formula and returns a path to a PDF."
  template = temp_env.get_template("formula.tex")
  tex = template.render({"formula": formula})
  (f, path) = tempfile.mkstemp()
  codecs.open(path, encoding="utf8", mode="w").write(tex)
  
  subprocess.check_output(["pdflatex",
    "-interaction=batchmode", "-output-dir=%s" % os.path.dirname(path),
    path])
  return path + ".pdf"

def _render_formula_as_image(formula):
  "Takes a LaTeX formula and returns a path to a PNG."
  pdfpath = _compile_formula_to_pdf(formula)

  dir = tempfile.mkdtemp()
  pngpath = dir + "/" + hashlib.md5(formula).hexdigest() + ".png"
  subprocess.check_output(["convert",
    "-density", "120", "-trim", "-transparent", "#FFFFFF",
    pdfpath, pngpath])

  return pngpath

def _render_formula(node, parsed, imgs):
  """
  Renders a formula tag.  If it has an img attribute, it will be rendered
  with LaTeX and the result will be included as an image.
  """
  formula = _render_content(node, parsed, imgs)["content"]
  as_img = node.get("img")
  content = ""
  if as_img:
    img_path = _render_formula_as_image(formula)
    if img_path:
      imgs.add(img_path)
      future_path = "imgs/" + os.path.basename(img_path)
      content = "<div class=\"formula\"><img src=\"%s\" alt=\"%s\" /></div>" % (future_path, formula)
    else:
      content = "<div class=\"formula\">%s</div>" % formula
  else:
    content = "<div class=\"formula\">\[ %s \]</div>" % formula
  return {"content": content, "imgs": imgs}

def _render_node(node, parsed, imgs):
  if type(node) in (str, unicode):
    return {"content": node, "imgs": imgs}
  r = _render_content(node, parsed, imgs)
  content = r["content"]
  if node.get("type") in BLOCK_TAGS:
    template = temp_env.get_template("block.html")
    return {"content": template.render({"block": dict_merge(node, {"content": content})}),
      "imgs": imgs}
  if node.get("type") == "paragraph":
    return {"content": "<p>%s</p>" % content, "imgs": imgs}
  if node.get("type") == "bold":
    return {"content": "<b>%s</b>" % content, "imgs": imgs}
  if node.get("type") == "italic":
    return {"content": "<i>%s</i>" % content, "imgs": imgs}
  if node.get("type") == "definition":
    return {"content": "<span class=\"definition\">%s</span>" % content,
      "imgs": imgs}
  if node.get("type") == "citation":
    return _render_citation(node, parsed, imgs)
  if node.get("type") == "term":
    return _render_term(node, parsed, imgs)
  if node.get("type") == "formula":
    return _render_formula(node, parsed, imgs)
  return r

def _render_par(par, parsed, imgs):
  content = ""
  for n in par.get("content"):
    r = _render_node(n, parsed, imgs)
    content += r["content"]
    imgs = r["imgs"]
  return {"content": content, "imgs": imgs}

def _escape_macros(macros):
  return [(k, v.replace("\\", "\\\\")) for (k, v) in macros.items()]

def render(parsed):
  """
  Takes a parsed hypertex file and renders it as HTML.  Returns a dict with
  the HTML in the `html` key and another key `imgs` which is a list of paths
  to auxiliary images (for formulas).
  """

  template = temp_env.get_template("template.html")
  imgs = set([])
  pars = []
  for p in parsed["body"]["pars"]:
    r = _render_par(p, parsed, imgs)
    pars.append(dict_merge(p, {"content": r["content"]}))
    imgs = r["imgs"]
  html = template.render({
    "title":   parsed["title"],
    "author":  parsed["author"],
    "macros":  _escape_macros(parsed["macros"]),
    "pars":    pars})
  return {"html": html, "imgs": imgs}

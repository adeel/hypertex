import hypertex.parser
import hypertex.render.html
import hypertex.render.tex

def render_html(htex, config={}):
  parsed = hypertex.parser.parse(htex)
  return hypertex.render.html.render(parsed, config)

def render_tex(htex):
  parsed = hypertex.parser.parse(htex)
  return hypertex.render.tex.render(parsed)

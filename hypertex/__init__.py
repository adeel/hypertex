import hypertex.parser
import hypertex.render.html
import hypertex.render.tex

def render_html(htex, parse_config={}, render_config={}):
  parsed = hypertex.parser.parse(htex, parse_config)
  return hypertex.render.html.render(parsed, render_config)

def render_tex(htex, parse_config={}, render_config={}):
  parsed = hypertex.parser.parse(htex, parse_config)
  return hypertex.render.tex.render(parsed, render_config)

"""Overlay HTML."""

OVERLAY_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0f;color:#ddd;
  font-family:'Segoe UI',sans-serif;
  padding:4px;user-select:none;
  -webkit-user-select:none;
  height:100vh;overflow:hidden
}
.content{
  -webkit-app-region:drag;
  height:100%;overflow-y:auto;
  padding:clamp(2px,1vw,6px)
}
.content::-webkit-scrollbar{width:clamp(3px,.8vw,5px)}
.content::-webkit-scrollbar-track{background:transparent}
.content::-webkit-scrollbar-thumb{
  background:#2a2a35;
  border-radius:clamp(2px,.4vw,3px)
}
.content::-webkit-scrollbar-thumb:hover{background:#3a3a48}
.cards-grid{
  display:flex;flex-wrap:wrap;
  gap:clamp(4px,1.2vw,7px)
}
.cards-grid .card{
  flex:1 1 clamp(170px,38vw,260px);
  margin-bottom:0
}
.cards-grid .mode-badge{flex:1 1 100%}
.card{
  background:#14141c;
  border-radius:clamp(4px,1.5vw,8px);
  padding:clamp(4px,1.2vw,7px) clamp(6px,2vw,12px);
  display:flex;
  gap:clamp(6px,1.5vw,10px);
  align-items:center;
  border:1px solid #2a2a35
}
.card-0{border-left:clamp(2px,.8vw,5px) solid #448cff}
.card-1{border-left:clamp(2px,.8vw,5px) solid #ff961e}
.rank-img{
  width:clamp(32px,9vw,52px);height:clamp(32px,9vw,52px);
  background:#1e1e2a;
  border-radius:clamp(3px,1vw,6px);
  display:flex;align-items:center;justify-content:center;
  font-size:clamp(6px,1.5vw,8px);
  color:#555;text-align:center;
  flex-shrink:0;line-height:1.2
}
.rank-icon{
  width:clamp(32px,9vw,52px);height:clamp(32px,9vw,52px);
  border-radius:clamp(3px,1vw,6px);
  object-fit:contain;flex-shrink:0;
  background:#1e1e2a
}
.info{flex:1;min-width:0;overflow:hidden}
.division-bars{
  display:flex;flex-direction:column;
  gap:clamp(1px,.3vw,2px);justify-content:center;
  padding-left:clamp(4px,1.2vw,7px);flex-shrink:0
}
.division-bar{
  width:clamp(14px,4vw,24px);height:clamp(2px,.5vw,3px);
  border-radius:clamp(1px,.3vw,2px)
}
.name{
  font-size:clamp(10px,2.5vw,13px);font-weight:600;color:#eee;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis
}
.mmr{font-size:clamp(12px,3vw,16px);font-weight:700;color:#fff;margin-top:1px}
.tier{
  font-size:clamp(8px,2vw,11px);color:#888;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis
}
.placeholder{
  text-align:center;
  padding:clamp(24px,8vw,48px) clamp(12px,4vw,24px);
  color:#555;font-size:clamp(11px,2.5vw,14px)
}
.mode-badge{
  text-align:center;font-size:clamp(9px,2vw,12px);
  color:#666;padding:clamp(2px,.8vw,5px) 0 clamp(4px,1.2vw,7px);
  -webkit-app-region:no-drag
}
.mode-hint{font-size:clamp(7px,1.5vw,9px);color:#444}
"""

PLACEHOLDER_HTML = "<div class=placeholder>Waiting for match…</div>"

_OVERLAY_JS = """\
function updateOverlay(html){document.getElementById('c').innerHTML=html}
function showWaiting(){document.getElementById('c').innerHTML='PLACEHOLDER'}
""".replace(
    "PLACEHOLDER", PLACEHOLDER_HTML
)

OVERLAY_HTML = f"""<!DOCTYPE html>
<html><head><meta charset=utf-8><style>{OVERLAY_CSS}</style></head>
<body>
<div class="content"><div id=c>{PLACEHOLDER_HTML}</div></div>
<script>{_OVERLAY_JS}</script>
</body></html>"""

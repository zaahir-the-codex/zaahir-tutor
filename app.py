from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Zaahir's Tutor - Test</title>
    <style>
        body { font-family: Arial; margin: 0; padding: 20px; background: #0f1117; color: white; }
        .menu-btn { 
            background: #7c9eff; 
            color: black; 
            padding: 15px 25px; 
            font-size: 20px; 
            border: none; 
            cursor: pointer; 
            border-radius: 8px;
            margin: 20px;
        }
        .menu-panel { 
            position: fixed; 
            top: 0; 
            left: -300px; 
            width: 280px; 
            height: 100%; 
            background: #1a1d2e; 
            transition: left 0.3s; 
            padding: 20px; 
            z-index: 1000;
            border-right: 1px solid #2d3148;
        }
        .menu-panel.open { left: 0; }
        .overlay { 
            display: none; 
            position: fixed; 
            top: 0; 
            left: 0; 
            right: 0; 
            bottom: 0; 
            background: rgba(0,0,0,0.5); 
            z-index: 999;
        }
        .overlay.open { display: block; }
        .close-btn { 
            background: #7c9eff; 
            border: none; 
            padding: 8px 15px; 
            cursor: pointer; 
            margin-top: 20px;
            border-radius: 5px;
        }
    </style>
</head>
<body>

<button class="menu-btn" id="menuButton">☰ OPEN MENU</button>

<div class="overlay" id="overlay"></div>
<div class="menu-panel" id="menuPanel">
    <h2>Menu</h2>
    <p>This is the menu!</p>
    <button class="close-btn" id="closeButton">Close Menu</button>
</div>

<script>
    console.log('Script loaded');
    
    const menuBtn = document.getElementById('menuButton');
    const closeBtn = document.getElementById('closeButton');
    const menuPanel = document.getElementById('menuPanel');
    const overlay = document.getElementById('overlay');
    
    console.log('Elements:', {menuBtn, closeBtn, menuPanel, overlay});
    
    function openMenu() {
        console.log('Opening menu');
        menuPanel.classList.add('open');
        overlay.classList.add('open');
    }
    
    function closeMenu() {
        console.log('Closing menu');
        menuPanel.classList.remove('open');
        overlay.classList.remove('open');
    }
    
    menuBtn.onclick = openMenu;
    closeBtn.onclick = closeMenu;
    overlay.onclick = closeMenu;
    
    console.log('Event handlers attached');
</script>

</body>
</html>
"""

@app.get("/")
async def home():
    return HTMLResponse(content=HTML)

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

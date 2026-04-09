* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', sans-serif;
    background: #0a0a0f;
    color: #fff;
    overflow-x: hidden;
}

/* 🌌 ГЛОБАЛЬНЫЙ ФОН */
body::before {
    content: '';
    position: fixed;
    width: 200%;
    height: 200%;
    background:
        radial-gradient(circle at 20% 30%, rgba(99,102,241,0.25), transparent),
        radial-gradient(circle at 80% 70%, rgba(236,72,153,0.25), transparent);
    animation: bgMove 40s linear infinite;
    z-index: 0;
}

@keyframes bgMove {
    to { transform: rotate(360deg); }
}

/* 🧱 LAYOUT */
.layout {
    display: flex;
    min-height: 100vh;
    position: relative;
    z-index: 2;
}

/* 🧭 SIDEBAR */
.sidebar {
    width: 240px;
    background: rgba(15,15,30,0.8);
    backdrop-filter: blur(20px);
    padding: 20px;
    border-right: 1px solid rgba(255,255,255,0.05);
}

.logo {
    font-weight: 800;
    margin-bottom: 30px;
}

.menu-item {
    display: block;
    padding: 12px;
    border-radius: 12px;
    color: #9ca3af;
    margin-bottom: 10px;
    transition: 0.3s;
}

.menu-item:hover {
    background: rgba(99,102,241,0.15);
    color: #fff;
}

.menu-item.active {
    background: linear-gradient(135deg,#6366f1,#ec4899);
    color: #fff;
    box-shadow: 0 0 20px rgba(99,102,241,0.5);
}

/* 📦 MAIN */
.main {
    flex: 1;
    padding: 40px;
}

.page-title {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 30px;
    background: linear-gradient(135deg,#6366f1,#ec4899);
    -webkit-background-clip: text;
    color: transparent;
}

/* 🔮 CARD */
.card {
    background: rgba(20,20,40,0.7);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 20px;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.05);
    transition: 0.3s;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 40px rgba(99,102,241,0.2);
}

/* 📊 PLATFORM */
.platform-card {
    display: flex;
    justify-content: space-between;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 15px;
    background: rgba(30,30,60,0.6);
    transition: 0.3s;
}

.platform-card:hover {
    transform: translateY(-3px) scale(1.01);
    box-shadow: 0 0 30px rgba(99,102,241,0.4);
}

.left {
    display: flex;
    gap: 12px;
    align-items: center;
}

.icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg,#6366f1,#ec4899);
}

.name {
    font-weight: 600;
}

.meta {
    font-size: 12px;
    color: #9ca3af;
}

.arrow {
    opacity: 0.5;
}

/* 📄 CHANNEL */
.channel {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

.channel:last-child {
    border: none;
}

.actions button {
    background: none;
    border: none;
    color: #aaa;
    cursor: pointer;
    margin-left: 10px;
}

.actions button:hover {
    color: #fff;
}

/* 🟣 BUTTON */
.btn {
    background: linear-gradient(135deg,#6366f1,#ec4899);
    border: none;
    padding: 10px 18px;
    border-radius: 12px;
    color: #fff;
    cursor: pointer;
    transition: 0.3s;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(99,102,241,0.5);
}

/* 📋 FORM */
.form {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap: 10px;
    margin-top: 15px;
}

.form input {
    padding: 10px;
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    background: rgba(15,15,30,0.7);
    color: #fff;
}

.form button {
    grid-column: span 3;
}

/* 📱 MOBILE */
@media(max-width:900px){
    .sidebar { display: none; }
    .form { grid-template-columns: 1fr; }
}
const supabaseUrl = "https://idbftfamynqdebxlazvv.supabase.co";
const supabaseAnonKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlkYmZ0ZmFteW5xZGVieGxhenZ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODExOTQ2NzEsImV4cCI6MjA5Njc3MDY3MX0.9uHMKNEhYI2NMjs2EG7es1pNR2bFtyQ9SLj7pQ-exfI";

window.supabaseClient = supabase.createClient(supabaseUrl, supabaseAnonKey);

// Intercept window.fetch
const originalFetch = window.fetch;
window.fetch = async function(resource, config) {
    if (typeof resource === 'string' && resource.includes('/api/test')) {
        // Mock a 200 OK response so APIManager thinks the server is online
        return new Response(JSON.stringify({ success: true, message: "Supabase Intercepted" }), {
            status: 200, headers: { 'Content-Type': 'application/json' }
        });
    }

    if (typeof resource === 'string' && resource.includes('/api/')) {
        // It's an API call, we need to map it to Supabase
        const endpoint = resource.split('/api/')[1].split('?')[0];
        const method = (config && config.method) ? config.method.toUpperCase() : 'GET';
        let body = null;
        if (config && config.body) {
            body = JSON.parse(config.body);
        }

        // Attach user_id to body if user is logged in and method is POST/PUT
        const { data: { session } } = await supabaseClient.auth.getSession();
        if (session && body) {
            body.user_id = session.user.id;
        }

        try {
            if (method === 'GET') {
                const { data, error } = await supabaseClient.from(endpoint).select('*');
                if (error) throw error;
                return new Response(JSON.stringify(data || []), { status: 200, headers: { 'Content-Type': 'application/json' } });
            } else if (method === 'POST') {
                const { data, error } = await supabaseClient.from(endpoint).insert(body).select();
                if (error) throw error;
                return new Response(JSON.stringify(data[0]), { status: 200, headers: { 'Content-Type': 'application/json' } });
            } else if (method === 'DELETE') {
                // Fetch uses query param: ?id=123
                const urlObj = new URL(resource, 'http://localhost');
                const id = urlObj.searchParams.get('id');
                const { error } = await supabaseClient.from(endpoint).delete().eq('id', id);
                if (error) throw error;
                return new Response(JSON.stringify({ success: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
            }
        } catch (err) {
            console.error("Supabase Interceptor Error:", err);
            return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: { 'Content-Type': 'application/json' } });
        }
    }

    return originalFetch(resource, config);
};

// UI adjustments when loaded
document.addEventListener("DOMContentLoaded", async () => {
    // Override API Badge directly
    setTimeout(() => {
        const badge = document.getElementById('apiStatusBadge');
        if (badge) badge.style.display = 'none';
        const fixedBadge = document.getElementById('fixedApiStatus');
        if (fixedBadge) fixedBadge.style.display = 'none';
        
        const apiModal = document.getElementById('apiModal');
        if (apiModal) apiModal.remove();
        
        const configBtn = document.querySelector('.tab-btn[onclick="switchTab(\'config-api\')"]');
        if (configBtn) configBtn.style.display = 'none';
    }, 500);

    // Setup Auth UI in Perfil page
    if (window.location.href.includes('perfil')) {
        const { data: { session } } = await supabaseClient.auth.getSession();
        
        if (!session) {
            // Show Login screen over Dashboard
            const dashboard = document.querySelector('.dashboard-container');
            if (dashboard) {
                dashboard.style.display = 'none';
                
                const loginDiv = document.createElement('div');
                loginDiv.innerHTML = `
                    <div style="max-width: 400px; margin: 40px auto; padding: 30px; background: #fff; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                        <h2 style="color: #5B8C5A; margin-bottom: 20px;">Acesso / Cadastro</h2>
                        <input type="email" id="sbEmail" placeholder="E-mail" style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 10px; border: 1px solid #ccc;">
                        <input type="password" id="sbPassword" placeholder="Senha" style="width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 10px; border: 1px solid #ccc;">
                        <button onclick="sbLogin()" style="width: 100%; padding: 12px; background: #5B8C5A; color: #fff; border: none; border-radius: 10px; cursor: pointer; font-weight: bold; margin-bottom: 10px;">Entrar</button>
                        <button onclick="sbSignup()" style="width: 100%; padding: 12px; background: #B8D8BA; color: #333; border: none; border-radius: 10px; cursor: pointer; font-weight: bold;">Cadastrar</button>
                        <p id="sbError" style="color: red; font-size: 0.8rem; margin-top: 10px;"></p>
                    </div>
                `;
                dashboard.parentNode.insertBefore(loginDiv, dashboard);
                
                window.sbLogin = async () => {
                    const e = document.getElementById('sbEmail').value;
                    const p = document.getElementById('sbPassword').value;
                    const { error } = await supabaseClient.auth.signInWithPassword({ email: e, password: p });
                    if (error) document.getElementById('sbError').innerText = error.message;
                    else window.location.reload();
                };
                
                window.sbSignup = async () => {
                    const e = document.getElementById('sbEmail').value;
                    const p = document.getElementById('sbPassword').value;
                    const { error } = await supabaseClient.auth.signUp({ email: e, password: p });
                    if (error) document.getElementById('sbError').innerText = error.message;
                    else alert("Cadastro realizado com sucesso! Faça login.");
                };
            }
        } else {
            // Logged in. Show logout button.
            const tabsHeader = document.querySelector('.tabs-header');
            if (tabsHeader) {
                const logoutBtn = document.createElement('button');
                logoutBtn.className = 'tab-btn';
                logoutBtn.innerText = 'Sair da Conta';
                logoutBtn.style.background = '#d9534f';
                logoutBtn.style.color = '#fff';
                logoutBtn.onclick = async () => {
                    await supabaseClient.auth.signOut();
                    window.location.reload();
                };
                tabsHeader.appendChild(logoutBtn);
            }
        }
    }
});

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") return new Response("OK");
    const body = await request.json();

    // 1. Handle command /start (FIX BUAT GRUP)
    // Pakai startsWith biar kebaca walaupun formatnya /start@NamaBot
    if (body.message && body.message.text && body.message.text.startsWith("/start")) {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, body.message.chat.id, 
        "🏛️ <b>HERMES Institutional Bot</b>\n\nSilakan pilih menu:", getMainMenu());
      return new Response("OK");
    }

    // 2. Handle Tombol (Callback Query)
    if (body.callback_query) {
      const cb = body.callback_query;
      const data = cb.data.split("|");
      const chatId = cb.message.chat.id;

      await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callback_query_id: cb.id, text: "Memproses..." })
      });

      // Menu Analisa (Pilih Model)
      if (data[0] === "menu" && data[1].startsWith("analisa")) {
        const model = data[1] === "analisa_deepseek" ? "deepseek" : "nemotron";
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          `Silakan pilih <b>Pair</b> (Analisa ${model.toUpperCase()}):`, getAssetsKeyboard(model));
      }
      // Pilih Pair -> Tembak GitHub
      else if (data[0] === "asset") {
        const symbol = data[1];
        const model = data[2];
        
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          `⏳ Menganalisa <b>${symbol}</b> pakai <b>${model.toUpperCase()}</b>...\nMohon tunggu.`);
        
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, symbol, model, null);
      }
      // Menu Journal
      else if (data[0] === "menu" && data[1] === "journal") {
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, "⏳ Membuka Journal...");
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, null, null, "journal");
      }
      // Menu Statistik & CSV
      else if (data[0] === "menu" && data[1] === "stats") {
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, "⏳ Membuat laporan dan grafik Winrate...");
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, null, null, "stats");
      }
      
      return new Response("OK");
    }
    return new Response("OK");
  },

  // 3. FUNGSI CRON OTOMATIS
  async scheduled(event, env, ctx) {
    const today = new Date().getUTCDay();
    
    if (today === 0 || today === 6) {
      console.log("Akhir pekan: Market tutup. Bot libur.");
      return; 
    }

    console.log("Hari kerja: Memicu Auto-Scan...");
    const cronModel = "deepseek"; 
    
    // --- PENTING: GANTI CHAT ID DI GITHUB KE ID GRUP ---
    await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, "XAUUSD", cronModel, "cron");
  }
};

// --- FUNGSI BANTUAN ---

async function sendTelegram(token, chatId, text, replyMarkup = null) {
  const payload = { chat_id: chatId, text: text, parse_mode: "HTML" };
  if (replyMarkup) payload.reply_markup = replyMarkup;
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
}

async function triggerGitHub(token, user, repo, symbol = null, model = null, cmd = null) {
  const inputs = {};
  if (symbol) inputs.symbol = symbol;
  if (model) inputs.model = model;
  if (cmd) inputs.cmd = cmd;

  return await fetch(`https://api.github.com/repos/${user}/${repo}/actions/workflows/agent.yml/dispatches`, {
    method: "POST",
    headers: { 
      "Authorization": `Bearer ${token}`, 
      "Accept": "application/vnd.github+json", 
      "User-Agent": "Cloudflare-Worker" 
    },
    body: JSON.stringify({ ref: "main", inputs: inputs })
  });
}

// --- FUNGSI KEYBOARD TELEGRAM ---

function getMainMenu() {
  return { inline_keyboard: [
    [{ text: "🧠 Analisa (DeepSeek)", callback_data: "menu|analisa_deepseek" }, { text: "⚡ Analisa (Nemotron)", callback_data: "menu|analisa_nemotron" }],
    [{ text: "📖 Journal", callback_data: "menu|journal" }, { text: "📈 Statistik & CSV", callback_data: "menu|stats" }]
  ]};
}

function getAssetsKeyboard(model) {
  return { inline_keyboard: [
    [{ text: "XAUUSD", callback_data: `asset|XAUUSD|${model}` }, { text: "BTCUSD", callback_data: `asset|BTCUSD|${model}` }],
    [{ text: "NASDAQ", callback_data: `asset|NASDAQ|${model}` }, { text: "EURUSD", callback_data: `asset|EURUSD|${model}` }],
    [{ text: "GBPUSD", callback_data: `asset|GBPUSD|${model}` }, { text: "USDJPY", callback_data: `asset|USDJPY|${model}` }]
  ]};
}

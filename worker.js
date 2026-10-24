export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") return new Response("OK");
    const body = await request.json();

    if (body.message && body.message.text === "/start") {
      await sendTelegram(env.TELEGRAM_BOT_TOKEN, body.message.chat.id, 
        "🏛️ <b>HERMES Institutional Bot</b>\n\nSilakan pilih menu:", getMainMenu());
      return new Response("OK");
    }

    if (body.callback_query) {
      const cb = body.callback_query;
      const data = cb.data.split("|");
      const chatId = cb.message.chat.id;

      await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/answerCallbackQuery`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ callback_query_id: cb.id, text: "Memproses..." })
      });

      // Menu Analisa (Pilih Model Dulu)
      if (data[0] === "menu" && data[1].startsWith("analisa")) {
        const model = data[1] === "analisa_deepseek" ? "deepseek" : "nemotron";
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          `Silakan pilih <b>Pair</b> (Analisa ${model.toUpperCase()}):`, getAssetsKeyboard(model));
      }
      // Pilih Pair -> Tembak GitHub (Bawa nama model)
      else if (data[0] === "asset") {
        const symbol = data[1];
        const model = data[2];
        
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          `⏳ Menganalisa <b>${symbol}</b> pakai <b>${model.toUpperCase()}</b>...\nMohon tunggu.`);
        
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, symbol, model);
      }
      // Journal
      else if (data[0] === "menu" && data[1] === "journal") {
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, "⏳ Membuka Journal...");
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, null, null, "journal");
      }
      return new Response("OK");
    }
    return new Response("OK");
  }
};

async function sendTelegram(token, chatId, text, replyMarkup = null) {
  const payload = { chat_id: chatId, text: text, parse_mode: "HTML" };
  if (replyMarkup) payload.reply_markup = replyMarkup;
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
}

async function triggerGitHub(token, user, repo, symbol, model = null, cmd = null) {
  const inputs = {};
  if (symbol) inputs.symbol = symbol;
  if (model) inputs.model = model;
  if (cmd) inputs.cmd = cmd;

  return await fetch(`https://api.github.com/repos/${user}/${repo}/actions/workflows/agent.yml/dispatches`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github+json", "User-Agent": "Cloudflare" },
    body: JSON.stringify({ ref: "main", inputs: inputs })
  });
}

function getMainMenu() {
  return { inline_keyboard: [
    [{ text: "🧠 Analisa (DeepSeek)", callback_data: "menu|analisa_deepseek" }, { text: "⚡ Analisa (Nemotron)", callback_data: "menu|analisa_nemotron" }],
    [{ text: "📖 Journal", callback_data: "menu|journal" }]
  ]};
}

function getAssetsKeyboard(model) {
  return { inline_keyboard: [
    [{ text: "XAUUSD", callback_data: `asset|XAUUSD|${model}` }, { text: "BTCUSD", callback_data: `asset|BTCUSD|${model}` }],
    [{ text: "NASDAQ", callback_data: `asset|NASDAQ|${model}` }, { text: "EURUSD", callback_data: `asset|EURUSD|${model}` }]
  ]};
}

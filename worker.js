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

      if (data[0] === "menu" && data[1] === "analisa") {
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          "Silakan pilih <b>Pair</b> (Analisa Otomatis MTF):", getAssetsKeyboard());
      }
      else if (data[0] === "asset") {
        const symbol = data[1];
        await sendTelegram(env.TELEGRAM_BOT_TOKEN, chatId, 
          `⏳ Menganalisa <b>${symbol}</b> (MTF + Fundamental)...\nMohon tunggu 1-2 menit.`);
        await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, symbol, null);
      }
      return new Response("OK");
    }
    return new Response("OK");
  },

  // FUNGSI CRON OTOMATIS
  async scheduled(event, env, ctx) {
    console.log("Cron berjalan: Memicu analisa otomatis...");
    // Lo bisa nambahin pair lain di sini nanti, misal NASDAQ
    await triggerGitHub(env.GITHUB_TOKEN, env.GITHUB_USER, env.GITHUB_REPO, "XAUUSD", "cron");
  }
};

async function sendTelegram(token, chatId, text, replyMarkup = null) {
  const payload = { chat_id: chatId, text: text, parse_mode: "HTML" };
  if (replyMarkup) payload.reply_markup = replyMarkup;
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
  });
}

async function triggerGitHub(token, user, repo, symbol, cmd = null) {
  const inputs = {};
  if (symbol) inputs.symbol = symbol;
  if (cmd) inputs.cmd = cmd;

  return await fetch(`https://api.github.com/repos/${user}/${repo}/actions/workflows/agent.yml/dispatches`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}`, "Accept": "application/vnd.github+json", "User-Agent": "Cloudflare" },
    body: JSON.stringify({ ref: "main", inputs: inputs })
  });
}

function getMainMenu() {
  return { inline_keyboard: [
    [{ text: "📊 1. Analisa Market", callback_data: "menu|analisa" }]
  ]};
}

function getAssetsKeyboard() {
  return { inline_keyboard: [
    [{ text: "XAUUSD", callback_data: "asset|XAUUSD" }, { text: "EURUSD", callback_data: "asset|EURUSD" }],
    [{ text: "GBPUSD", callback_data: "asset|GBPUSD" }, { text: "USDJPY", callback_data: "asset|USDJPY" }],
    [{ text: "NASDAQ", callback_data: "asset|NASDAQ" }, { text: "BTCUSD", callback_data: "asset|BTCUSD" }]
  ]};
}

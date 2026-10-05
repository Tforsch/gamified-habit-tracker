using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Telegram.Bot;
using Telegram.Bot.Polling;
using Telegram.Bot.Types;
using Telegram.Bot.Types.Enums;
using Telegram.Bot.Types.ReplyMarkups;

namespace HeroQuestBot;

public class Program
{
    // In-memory player database by Telegram User ID
    private static readonly ConcurrentDictionary<long, PlayerState> Players = new();

    public static async Task Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.WriteLine("=================================================");
        Console.WriteLine("⚔️  HeroQuest Telegram Bot (RPG Habit Companion)");
        Console.WriteLine("=================================================");

        // Read token from argument, environment variable, or prompt
        string? botToken = Environment.GetEnvironmentVariable("TELEGRAM_BOT_TOKEN");
        if (string.IsNullOrWhiteSpace(botToken) && args.Length > 0)
        {
            botToken = args[0];
        }

        while (string.IsNullOrWhiteSpace(botToken))
        {
            Console.WriteLine("\n[?] Для запуску бота потрібен токен від @BotFather.");
            Console.WriteLine("    Якщо у вас вже є токен, вставте його сюди й натисніть Enter.");
            Console.Write("👉 Введіть Telegram Bot Token: ");
            botToken = Console.ReadLine()?.Trim();
        }

        var botClient = new TelegramBotClient(botToken);

        using var cts = new CancellationTokenSource();

        var receiverOptions = new ReceiverOptions
        {
            AllowedUpdates = new[] { UpdateType.Message, UpdateType.CallbackQuery }
        };

        botClient.StartReceiving(
            updateHandler: HandleUpdateAsync,
            errorHandler: HandleErrorAsync,
            receiverOptions: receiverOptions,
            cancellationToken: cts.Token
        );

        var me = await botClient.GetMe(cts.Token);
        Console.WriteLine($"\n✅ Бот успішно підключився до Telegram!");
        Console.WriteLine($"🤖 Ім'я бота: @{me.Username} ({me.FirstName})");
        Console.WriteLine($"🌐 Відкрийте Telegram і напишіть боту: https://t.me/{me.Username}");
        Console.WriteLine("Натисніть Ctrl+C для зупинки.\n");

        // Keep running until canceled
        await Task.Delay(Timeout.Infinite, cts.Token);
    }

    private static async Task HandleUpdateAsync(ITelegramBotClient bot, Update update, CancellationToken cancellationToken)
    {
        try
        {
            if (update.Message is { } message && !string.IsNullOrEmpty(message.Text))
            {
                await HandleMessageAsync(bot, message, cancellationToken);
            }
            else if (update.CallbackQuery is { } callbackQuery)
            {
                await HandleCallbackQueryAsync(bot, callbackQuery, cancellationToken);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Помилка обробки: {ex.Message}");
        }
    }

    private static async Task HandleMessageAsync(ITelegramBotClient bot, Message message, CancellationToken ct)
    {
        long userId = message.From?.Id ?? message.Chat.Id;
        string userName = message.From?.FirstName ?? "Герой";

        var player = Players.GetOrAdd(userId, _ => new PlayerState(userName));

        string text = message.Text?.Trim().ToLowerInvariant() ?? "";

        if (text.StartsWith("/start") || text.StartsWith("меню"))
        {
            string welcomeText =
                $"🧙‍♂️ <b>Вітаємо у гільдії героїв, {player.Name}!</b>\n\n" +
                $"Це твій персональний RPG-трекер звичок.\n" +
                $"Виконуй щоденні квести, отримуй <b>XP</b>, піднімай рівень і стережися опівночі — невиконані дейліки забирають <b>HP</b>!\n\n" +
                $"Обери дію у меню нижче:";

            await bot.SendMessage(
                chatId: message.Chat.Id,
                text: welcomeText,
                parseMode: ParseMode.Html,
                replyMarkup: GetMainMenuKeyboard(),
                cancellationToken: ct
            );
        }
        else if (text.StartsWith("/quests") || text.Contains("квест"))
        {
            await SendQuestsListAsync(bot, message.Chat.Id, player, ct);
        }
        else if (text.StartsWith("/profile") || text.Contains("профіль"))
        {
            await SendProfileAsync(bot, message.Chat.Id, player, ct);
        }
        else
        {
            await bot.SendMessage(
                chatId: message.Chat.Id,
                text: "⚔️ Скористайтеся меню нижче або напишіть /start для перегляду квестів.",
                replyMarkup: GetMainMenuKeyboard(),
                cancellationToken: ct
            );
        }
    }

    private static async Task HandleCallbackQueryAsync(ITelegramBotClient bot, CallbackQuery callback, CancellationToken ct)
    {
        long userId = callback.From.Id;
        long chatId = callback.Message?.Chat.Id ?? userId;
        int messageId = callback.Message?.Id ?? 0;

        var player = Players.GetOrAdd(userId, _ => new PlayerState(callback.From.FirstName));

        string data = callback.Data ?? "";

        if (data == "menu_quests")
        {
            await SendQuestsListAsync(bot, chatId, player, ct, messageId);
        }
        else if (data == "menu_profile")
        {
            await SendProfileAsync(bot, chatId, player, ct, messageId);
        }
        else if (data == "menu_deadline")
        {
            var now = DateTime.UtcNow;
            var tomorrow = DateTime.UtcNow.Date.AddDays(1);
            var remaining = tomorrow - now;

            string timerText =
                $"⏳ <b>Час до опівнічного дедлайну:</b>\n\n" +
                $"🕒 Залишилося: <b>{remaining.Hours:D2} год {remaining.Minutes:D2} хв {remaining.Seconds:D2} сек</b>\n\n" +
                $"⚠️ <i>Рівно о 00:00 UTC невиконані квести завдадуть шкоди вашому HP (-10 за кожен)!</i>";

            await bot.AnswerCallbackQuery(callback.Id, "Таймер оновлено", cancellationToken: ct);
            if (messageId > 0)
            {
                await bot.EditMessageText(
                    chatId: chatId,
                    messageId: messageId,
                    text: timerText,
                    parseMode: ParseMode.Html,
                    replyMarkup: GetBackToMenuKeyboard(),
                    cancellationToken: ct
                );
            }
        }
        else if (data == "menu_chest")
        {
            var rnd = new Random();
            int roll = rnd.Next(1, 21); // d20
            int bonusXp = roll * 2;

            player.GainXp(bonusXp);

            string chestText =
                $"🎲 <b>Ви відкрили щоденну скриню луту!</b>\n\n" +
                $"Кидок кубика d20: 🎯 <b>{roll}</b>\n" +
                $"✨ Знахідка принесла вам: <b>+{bonusXp} XP</b>!\n\n" +
                $"Поточний досвід: <b>{player.CurrentXp} / {player.NextLevelXp} XP</b>";

            await bot.AnswerCallbackQuery(callback.Id, $"🎲 +{bonusXp} XP здобуто!", showAlert: true, cancellationToken: ct);
            if (messageId > 0)
            {
                await bot.EditMessageText(
                    chatId: chatId,
                    messageId: messageId,
                    text: chestText,
                    parseMode: ParseMode.Html,
                    replyMarkup: GetBackToMenuKeyboard(),
                    cancellationToken: ct
                );
            }
        }
        else if (data.StartsWith("complete_"))
        {
            string questId = data.Replace("complete_", "");
            var quest = player.Quests.FirstOrDefault(q => q.Id == questId);

            if (quest != null && !quest.IsCompleted)
            {
                quest.IsCompleted = true;
                bool leveledUp = player.GainXp(quest.XpReward);

                string popup = leveledUp
                    ? $"🎉 РІВЕНЬ ПІДВИЩЕНО! Тепер ви Рівень {player.Level}!"
                    : $"✨ Квест виконано! +{quest.XpReward} XP!";

                await bot.AnswerCallbackQuery(callback.Id, popup, showAlert: true, cancellationToken: ct);
                await SendQuestsListAsync(bot, chatId, player, ct, messageId);
            }
            else
            {
                await bot.AnswerCallbackQuery(callback.Id, "Цей квест уже завершено сьогодні!", cancellationToken: ct);
            }
        }
        else if (data == "menu_main")
        {
            string welcomeText =
                $"🧙‍♂️ <b>Головне меню героїв</b>\n\n" +
                $"Герой: <b>{player.Name}</b> (Рівень {player.Level})\n" +
                $"Оберіть пункт:";

            await bot.AnswerCallbackQuery(callback.Id, cancellationToken: ct);
            if (messageId > 0)
            {
                await bot.EditMessageText(
                    chatId: chatId,
                    messageId: messageId,
                    text: welcomeText,
                    parseMode: ParseMode.Html,
                    replyMarkup: GetMainMenuKeyboard(),
                    cancellationToken: ct
                );
            }
        }
    }

    private static async Task SendQuestsListAsync(ITelegramBotClient bot, long chatId, PlayerState player, CancellationToken ct, int editMessageId = 0)
    {
        string text = "⚔️ <b>Ваші щоденні дейліки на сьогодні:</b>\n\n";

        var inlineButtons = new List<InlineKeyboardButton[]>();

        foreach (var q in player.Quests)
        {
            string statusIcon = q.IsCompleted ? "✅" : "⏳";
            string titleText = q.IsCompleted ? $"<s>{q.Title}</s> (Виконано)" : q.Title;
            text += $"{statusIcon} <b>{titleText}</b>\n    ✨ +{q.XpReward} XP | 💔 -10 HP о 00:00\n\n";

            if (!q.IsCompleted)
            {
                inlineButtons.Add(new[]
                {
                    InlineKeyboardButton.WithCallbackData($"⚡ Виконати: {q.Title}", $"complete_{q.Id}")
                });
            }
        }

        inlineButtons.Add(new[]
        {
            InlineKeyboardButton.WithCallbackData("🔄 Оновити", "menu_quests"),
            InlineKeyboardButton.WithCallbackData("🔙 Головне меню", "menu_main")
        });

        var markup = new InlineKeyboardMarkup(inlineButtons);

        if (editMessageId > 0)
        {
            await bot.EditMessageText(chatId, editMessageId, text, ParseMode.Html, replyMarkup: markup, cancellationToken: ct);
        }
        else
        {
            await bot.SendMessage(chatId, text, ParseMode.Html, replyMarkup: markup, cancellationToken: ct);
        }
    }

    private static async Task SendProfileAsync(ITelegramBotClient bot, long chatId, PlayerState player, CancellationToken ct, int editMessageId = 0)
    {
        int hpPercent = (int)((double)player.Hp / player.MaxHp * 10);
        string hpBar = new string('█', Math.Clamp(hpPercent, 0, 10)) + new string('░', Math.Max(0, 10 - hpPercent));

        int xpPercent = (int)((double)player.CurrentXp / player.NextLevelXp * 10);
        string xpBar = new string('█', Math.Clamp(xpPercent, 0, 10)) + new string('░', Math.Max(0, 10 - xpPercent));

        string profileText =
            $"🧙‍♂️ <b>Профіль Героя</b>\n\n" +
            $"👤 Ім'я: <b>{player.Name}</b>\n" +
            $"⭐ Рівень: <b>{player.Level}</b>\n" +
            $"❤️ HP: <b>{player.Hp}/{player.MaxHp}</b>\n<code>[{hpBar}]</code>\n\n" +
            $"⚡ XP: <b>{player.CurrentXp}/{player.NextLevelXp}</b>\n<code>[{xpBar}]</code>\n\n" +
            $"🔥 Стрік активності: <b>3 дні</b>";

        if (editMessageId > 0)
        {
            await bot.EditMessageText(chatId, editMessageId, profileText, ParseMode.Html, replyMarkup: GetBackToMenuKeyboard(), cancellationToken: ct);
        }
        else
        {
            await bot.SendMessage(chatId, profileText, ParseMode.Html, replyMarkup: GetBackToMenuKeyboard(), cancellationToken: ct);
        }
    }

    private static InlineKeyboardMarkup GetMainMenuKeyboard()
    {
        return new InlineKeyboardMarkup(new[]
        {
            new[]
            {
                InlineKeyboardButton.WithCallbackData("⚔️ Мої квести", "menu_quests"),
                InlineKeyboardButton.WithCallbackData("🧙‍♂️ Профіль", "menu_profile")
            },
            new[]
            {
                InlineKeyboardButton.WithCallbackData("⏳ До дедлайну", "menu_deadline"),
                InlineKeyboardButton.WithCallbackData("🎲 Скриня луту", "menu_chest")
            }
        });
    }

    private static InlineKeyboardMarkup GetBackToMenuKeyboard()
    {
        return new InlineKeyboardMarkup(new[]
        {
            new[] { InlineKeyboardButton.WithCallbackData("🔙 Назад у меню", "menu_main") }
        });
    }

    private static Task HandleErrorAsync(ITelegramBotClient bot, Exception ex, HandleErrorSource source, CancellationToken ct)
    {
        Console.WriteLine($"[Error] {ex.Message}");
        return Task.CompletedTask;
    }
}

public class PlayerState
{
    public string Name { get; set; }
    public int Level { get; set; } = 1;
    public int CurrentXp { get; set; } = 0;
    public int NextLevelXp { get; set; } = 100;
    public int Hp { get; set; } = 100;
    public int MaxHp { get; set; } = 100;
    public List<QuestItem> Quests { get; set; }

    public PlayerState(string name)
    {
        Name = name;
        Quests = new List<QuestItem>
        {
            new("q1", "💧 Випити 2л води", 15),
            new("q2", "💻 Програмувати 45 хв", 35),
            new("q3", "📖 Прочитати 15 сторінок", 25)
        };
    }

    public bool GainXp(int amount)
    {
        CurrentXp += amount;
        bool leveledUp = false;
        while (CurrentXp >= NextLevelXp)
        {
            CurrentXp -= NextLevelXp;
            Level += 1;
            NextLevelXp = (int)(100 * Math.Pow(Level, 1.5));
            leveledUp = true;
        }
        return leveledUp;
    }
}

public class QuestItem
{
    public string Id { get; set; }
    public string Title { get; set; }
    public int XpReward { get; set; }
    public bool IsCompleted { get; set; }

    public QuestItem(string id, string title, int xpReward)
    {
        Id = id;
        Title = title;
        XpReward = xpReward;
        IsCompleted = false;
    }
}

using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);

// Configure URL to http://localhost:5000
builder.WebHost.UseUrls("http://localhost:5000");

// Add CORS support
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();

app.UseCors();

// Locate the frontend directory (c:\Users\f16\Downloads\HTML\frontend)
var frontendPath = Path.GetFullPath(Path.Combine(app.Environment.ContentRootPath, "..", "frontend"));
if (Directory.Exists(frontendPath))
{
    var fileProvider = new PhysicalFileProvider(frontendPath);

    // Serve static files (styles, scripts, images)
    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = fileProvider,
        RequestPath = ""
    });

    // Default file serving (index.html for root)
    app.UseDefaultFiles(new DefaultFilesOptions
    {
        FileProvider = fileProvider,
        DefaultFileNames = new List<string> { "index.html" }
    });

    app.UseStaticFiles(new StaticFileOptions
    {
        FileProvider = fileProvider,
        RequestPath = ""
    });
}

// ==========================================
// In-Memory Data Models & Gamification State
// ==========================================
var player = new Player
{
    Id = "usr_001",
    Name = "Hero",
    Level = 1,
    CurrentXp = 45,
    NextLevelXp = 100,
    Hp = 100,
    MaxHp = 100,
    Streak = 3
};

var habits = new List<Habit>
{
    new Habit { Id = "hab_001", Title = "Drink 2L Water", Difficulty = "EASY", XpReward = 15, HpPenalty = 5, Streak = 4, CompletedToday = false },
    new Habit { Id = "hab_002", Title = "Code for 45 minutes", Difficulty = "MEDIUM", XpReward = 35, HpPenalty = 15, Streak = 2, CompletedToday = false }
};

// ==========================================
// REST API Endpoints (/api/v1)
// ==========================================

app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }));

app.MapGet("/api/v1/users/me", () => Results.Ok(player));

app.MapGet("/api/v1/habits", () => Results.Ok(habits));

app.MapPost("/api/v1/habits", (CreateHabitRequest req) =>
{
    if (string.IsNullOrWhiteSpace(req.Title))
        return Results.BadRequest(new { error = "Title is required" });

    var newHabit = new Habit
    {
        Id = $"hab_{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}",
        Title = req.Title,
        Difficulty = req.Difficulty ?? "MEDIUM",
        XpReward = req.XpReward > 0 ? req.XpReward : 25,
        HpPenalty = req.HpPenalty > 0 ? req.HpPenalty : 10,
        Streak = 0,
        CompletedToday = false
    };

    habits.Add(newHabit);
    return Results.Created($"/api/v1/habits/{newHabit.Id}", newHabit);
});

app.MapPost("/api/v1/habits/{id}/complete", (string id) =>
{
    var habit = habits.FirstOrDefault(h => h.Id == id);
    if (habit == null)
        return Results.NotFound(new { error = "Habit not found" });

    if (habit.CompletedToday)
        return Results.BadRequest(new { error = "Habit already completed today" });

    habit.CompletedToday = true;
    habit.Streak += 1;

    // Gamification Engine: XP & Level calculations
    player.CurrentXp += habit.XpReward;
    while (player.CurrentXp >= player.NextLevelXp)
    {
        player.CurrentXp -= player.NextLevelXp;
        player.Level += 1;
        player.NextLevelXp = (int)(100 * Math.Pow(player.Level, 1.5));
    }

    return Results.Ok(new
    {
        message = "Quest completed successfully!",
        habit,
        player,
        habits
    });
});

// Fallback for SPA routing to index.html if not API
if (Directory.Exists(frontendPath))
{
    app.MapFallbackToFile("index.html", new StaticFileOptions
    {
        FileProvider = new PhysicalFileProvider(frontendPath)
    });
}

Console.WriteLine("=====================================================");
Console.WriteLine("⚔️  Gamified Habit Tracker is running!");
Console.WriteLine("🌐 Open in your browser: http://localhost:5000");
Console.WriteLine("📋 REST API Endpoint:   http://localhost:5000/api/v1");
Console.WriteLine("=====================================================");

app.Run();

// ==========================================
// DTOs & Domain Classes
// ==========================================
public class Player
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public int Level { get; set; }
    public int CurrentXp { get; set; }
    public int NextLevelXp { get; set; }
    public int Hp { get; set; }
    public int MaxHp { get; set; }
    public int Streak { get; set; }
}

public class Habit
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string Difficulty { get; set; } = "MEDIUM";
    public int XpReward { get; set; }
    public int HpPenalty { get; set; }
    public int Streak { get; set; }
    public bool CompletedToday { get; set; }
}

public class CreateHabitRequest
{
    public string? Title { get; set; }
    public string? Difficulty { get; set; }
    public int XpReward { get; set; }
    public int HpPenalty { get; set; }
}

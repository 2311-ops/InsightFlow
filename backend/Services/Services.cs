using System.Text;
using System.Text.Json;
using InsightFlow.Backend.Data;
using InsightFlow.Backend.Models;
using Microsoft.EntityFrameworkCore;

namespace InsightFlow.Backend.Services;

// ── AI Engine HTTP Client ─────────────────────────────────────────
public class AIService
{
    private readonly HttpClient _client;
    private readonly IConfiguration _config;

    public AIService(HttpClient client, IConfiguration config)
    {
        _client = client;
        _config = config;
        _client.BaseAddress = new Uri(_config["AIEngine:BaseUrl"]!);
    }

    public async Task<string> GetInsightAsync(string metricsJson)
    {
        var content = new StringContent(metricsJson, Encoding.UTF8, "application/json");
        var response = await _client.PostAsync("/ai/insights", content);

        if (!response.IsSuccessStatusCode)
            return "AI engine unavailable.";

        var result = await response.Content.ReadAsStringAsync();
        return result;
    }

    public async Task<string> AskQuestionAsync(string question, string metricsJson)
    {
        var payload = JsonSerializer.Serialize(new { question, metrics = metricsJson });
        var content = new StringContent(payload, Encoding.UTF8, "application/json");
        var response = await _client.PostAsync("/ai/ask", content);

        if (!response.IsSuccessStatusCode)
            return "AI engine unavailable.";

        return await response.Content.ReadAsStringAsync();
    }
}

// ── Dataset Service ───────────────────────────────────────────────
public class DatasetService
{
    private readonly AppDbContext _db;
    private readonly IWebHostEnvironment _env;

    public DatasetService(AppDbContext db, IWebHostEnvironment env)
    {
        _db = db;
        _env = env;
    }

    public async Task<Dataset> SaveDatasetAsync(IFormFile file, int companyId)
    {
        var uploadsDir = Path.Combine(_env.ContentRootPath, "uploads");
        Directory.CreateDirectory(uploadsDir);

        var fileName = $"{Guid.NewGuid()}_{file.FileName}";
        var filePath = Path.Combine(uploadsDir, fileName);

        await using var stream = new FileStream(filePath, FileMode.Create);
        await file.CopyToAsync(stream);

        var dataset = new Dataset
        {
            FileName = file.FileName,
            FilePath = filePath,
            FileSizeBytes = file.Length,
            CompanyId = companyId,
            Status = "uploaded",
        };

        _db.Datasets.Add(dataset);
        await _db.SaveChangesAsync();
        return dataset;
    }

    public async Task<List<Dataset>> GetDatasetsForCompanyAsync(int companyId)
        => await _db.Datasets
            .Where(d => d.CompanyId == companyId)
            .OrderByDescending(d => d.UploadedAt)
            .ToListAsync();
}

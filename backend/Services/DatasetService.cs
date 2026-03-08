// Phase 2
using System.Text.Json;
using InsightFlow.Backend.Data;
using InsightFlow.Backend.Models;
using Microsoft.EntityFrameworkCore;

namespace InsightFlow.Backend.Services;

public class DatasetService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IWebHostEnvironment _environment;

    public DatasetService(IServiceScopeFactory scopeFactory, IWebHostEnvironment environment)
    {
        _scopeFactory = scopeFactory;
        _environment = environment;
    }

    public async Task<Dataset> SaveDatasetAsync(IFormFile file, int companyId)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        var uploadsDir = Path.Combine(_environment.ContentRootPath, "uploads");
        Directory.CreateDirectory(uploadsDir);

        var fileName = $"{Guid.NewGuid()}_{Path.GetFileName(file.FileName)}";
        var filePath = Path.Combine(uploadsDir, fileName);

        await using (var stream = new FileStream(filePath, FileMode.Create))
        {
            await file.CopyToAsync(stream);
        }

        var dataset = new Dataset
        {
            FileName = file.FileName,
            FilePath = filePath,
            FileSizeBytes = file.Length,
            CompanyId = companyId,
            Status = "uploaded"
        };

        db.Datasets.Add(dataset);
        await db.SaveChangesAsync();

        return dataset;
    }

    public async Task ProcessDatasetAsync(int datasetId)
    {
        using var scope = _scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var ai = scope.ServiceProvider.GetRequiredService<AIService>();

        var dataset = await db.Datasets.FirstOrDefaultAsync(d => d.DatasetId == datasetId);
        if (dataset is null)
        {
            return;
        }

        try
        {
            dataset.Status = "processing";
            await db.SaveChangesAsync();

            var payloadJson = JsonSerializer.Serialize(new
            {
                file_path = dataset.FilePath,
                dataset_id = dataset.DatasetId
            });

            var aiResponseJson = await ai.ProcessFileAsync(payloadJson);
            using var doc = JsonDocument.Parse(aiResponseJson);

            var root = doc.RootElement;
            var metricsElement = root.GetProperty("metrics");
            var insight = root.TryGetProperty("insight", out var insightElement)
                ? insightElement.GetString() ?? string.Empty
                : string.Empty;

            foreach (var metricProperty in metricsElement.EnumerateObject())
            {
                if (metricProperty.Value.ValueKind != JsonValueKind.Number)
                {
                    continue;
                }

                if (!metricProperty.Value.TryGetDouble(out var metricValue))
                {
                    continue;
                }

                db.Metrics.Add(new Metric
                {
                    DatasetId = dataset.DatasetId,
                    Name = metricProperty.Name,
                    Value = metricValue,
                    Unit = InferUnit(metricProperty.Name)
                });
            }

            if (!string.IsNullOrWhiteSpace(insight))
            {
                db.Insights.Add(new Insight
                {
                    DatasetId = dataset.DatasetId,
                    Content = insight,
                    Type = "general"
                });
            }

            dataset.Status = "done";
            await db.SaveChangesAsync();
        }
        catch
        {
            dataset.Status = "error";
            await db.SaveChangesAsync();
            throw;
        }
    }

    public static string InferUnit(string metricName)
    {
        var name = metricName.ToLowerInvariant();

        if (name.Contains("revenue") || name.Contains("price") || name.Contains("cost"))
        {
            return "USD";
        }

        if (name.Contains("pct") || name.Contains("rate") || name.Contains("growth"))
        {
            return "%";
        }

        if (name.Contains("count") || name.Contains("rows"))
        {
            return "count";
        }

        return "value";
    }
}

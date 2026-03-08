// Phase 2
using System.Security.Claims;
using System.Text.Json;
using InsightFlow.Backend.Data;
using InsightFlow.Backend.Models;
using InsightFlow.Backend.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace InsightFlow.Backend.Controllers;

[ApiController]
[Authorize]
[Route("api/insights")]
public class InsightsController : ControllerBase
{
    private readonly AppDbContext _db;
    private readonly AIService _aiService;

    public InsightsController(AppDbContext db, AIService aiService)
    {
        _db = db;
        _aiService = aiService;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<Insight>>> GetInsights([FromQuery] int datasetId)
    {
        var userId = GetCurrentUserId();
        var ownsDataset = await _db.Datasets.Include(d => d.Company)
            .AnyAsync(d => d.DatasetId == datasetId && d.Company.UserId == userId);
        if (!ownsDataset)
        {
            return NotFound();
        }

        var insights = await _db.Insights
            .Where(i => i.DatasetId == datasetId)
            .OrderByDescending(i => i.GeneratedAt)
            .ToListAsync();

        return Ok(insights);
    }

    [HttpPost("ask")]
    public async Task<ActionResult<Insight>> AskQuestion([FromBody] AskInsightRequest request)
    {
        var dataset = await GetUserDatasetAsync(request.DatasetId);
        if (dataset is null)
        {
            return NotFound();
        }

        var metricsJson = JsonSerializer.Serialize(dataset.Metrics.ToDictionary(m => m.Name, m => m.Value));
        var rawResponse = await _aiService.AskQuestionAsync(request.Question, metricsJson);
        var answer = ExtractStringField(rawResponse, "answer") ?? rawResponse;

        var insight = new Insight
        {
            DatasetId = request.DatasetId,
            Content = answer,
            Type = "qa"
        };

        _db.Insights.Add(insight);
        await _db.SaveChangesAsync();

        return Ok(insight);
    }

    [HttpPost("regenerate")]
    public async Task<ActionResult<Insight>> Regenerate([FromBody] DatasetRequest request)
    {
        var dataset = await GetUserDatasetAsync(request.DatasetId);
        if (dataset is null)
        {
            return NotFound();
        }

        var payloadJson = JsonSerializer.Serialize(new
        {
            metrics = dataset.Metrics.ToDictionary(m => m.Name, m => m.Value)
        });

        var rawResponse = await _aiService.GetInsightAsync(payloadJson);
        var content = ExtractStringField(rawResponse, "insight") ?? rawResponse;

        var insight = new Insight
        {
            DatasetId = request.DatasetId,
            Content = content,
            Type = "general"
        };

        _db.Insights.Add(insight);
        await _db.SaveChangesAsync();

        return Ok(insight);
    }

    private async Task<Dataset?> GetUserDatasetAsync(int datasetId)
    {
        var userId = GetCurrentUserId();
        return await _db.Datasets
            .Include(d => d.Company)
            .Include(d => d.Metrics)
            .FirstOrDefaultAsync(d => d.DatasetId == datasetId && d.Company.UserId == userId);
    }

    private static string? ExtractStringField(string json, string field)
    {
        try
        {
            using var document = JsonDocument.Parse(json);
            if (document.RootElement.TryGetProperty(field, out var element))
            {
                return element.GetString();
            }
        }
        catch
        {
        }

        return null;
    }

    private int GetCurrentUserId()
    {
        var claim = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!int.TryParse(claim, out var userId))
        {
            throw new UnauthorizedAccessException("Invalid user context.");
        }

        return userId;
    }

    public record AskInsightRequest(int DatasetId, string Question);
    public record DatasetRequest(int DatasetId);
    public record InsightResponse(string Insight);
    public record MetricsRequest(Dictionary<string, object> Metrics, int DatasetId);

    // Phase 3
    [HttpPost("metrics")]
    public async Task<ActionResult<InsightResponse>> PostMetrics([FromBody] MetricsRequest request)
    {
        if (request == null)                        // null‑body guard
            return BadRequest();

        try
        {
            var payloadJson = JsonSerializer.Serialize(new { metrics = request.Metrics });
            var rawResponse = await _aiService.GetInsightAsync(payloadJson);
            var insight = ExtractStringField(rawResponse, "insight") ?? rawResponse;
            return Ok(new InsightResponse(insight));
        }
        catch (Exception ex)                        // don’t leak stack traces
        {
            return StatusCode(500, new { error = ex.Message });
        }
    }
}

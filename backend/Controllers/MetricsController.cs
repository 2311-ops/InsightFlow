// Phase 2
using System.Security.Claims;
using InsightFlow.Backend.Data;
using InsightFlow.Backend.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace InsightFlow.Backend.Controllers;

[ApiController]
[Authorize]
[Route("api/metrics")]
public class MetricsController : ControllerBase
{
    private readonly AppDbContext _db;

    public MetricsController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<Metric>>> GetMetrics([FromQuery] int datasetId)
    {
        var userId = GetCurrentUserId();
        var ownsDataset = await _db.Datasets.Include(d => d.Company)
            .AnyAsync(d => d.DatasetId == datasetId && d.Company.UserId == userId);
        if (!ownsDataset)
        {
            return NotFound();
        }

        var metrics = await _db.Metrics.Where(m => m.DatasetId == datasetId).OrderBy(m => m.Name).ToListAsync();
        return Ok(metrics);
    }

    [HttpGet("summary")]
    public async Task<ActionResult<object>> GetSummary([FromQuery] int datasetId)
    {
        var userId = GetCurrentUserId();
        var ownsDataset = await _db.Datasets.Include(d => d.Company)
            .AnyAsync(d => d.DatasetId == datasetId && d.Company.UserId == userId);
        if (!ownsDataset)
        {
            return NotFound();
        }

        var grouped = await _db.Metrics
            .Where(m => m.DatasetId == datasetId)
            .GroupBy(m => m.Unit)
            .Select(g => new
            {
                unit = g.Key,
                metrics = g.Select(m => new { m.MetricId, m.Name, m.Value }).ToList()
            })
            .ToListAsync();

        return Ok(grouped);
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
}

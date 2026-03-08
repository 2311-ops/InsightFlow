// Phase 2
using System.Security.Claims;
using InsightFlow.Backend.Data;
using InsightFlow.Backend.Models;
using InsightFlow.Backend.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace InsightFlow.Backend.Controllers;

[ApiController]
[Authorize]
[Route("api/datasets")]
public class DatasetsController : ControllerBase
{
    private static readonly string[] AllowedExtensions = [".csv", ".xlsx", ".xls"];
    private readonly AppDbContext _db;
    private readonly DatasetService _datasetService;

    public DatasetsController(AppDbContext db, DatasetService datasetService)
    {
        _db = db;
        _datasetService = datasetService;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<Dataset>>> GetDatasets([FromQuery] int companyId)
    {
        var userId = GetCurrentUserId();
        var ownsCompany = await _db.Companies.AnyAsync(c => c.CompanyId == companyId && c.UserId == userId);
        if (!ownsCompany)
        {
            return NotFound();
        }

        var datasets = await _db.Datasets
            .Where(d => d.CompanyId == companyId)
            .OrderByDescending(d => d.UploadedAt)
            .ToListAsync();

        return Ok(datasets);
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<Dataset>> GetDatasetById(int id)
    {
        var userId = GetCurrentUserId();
        var dataset = await _db.Datasets
            .Include(d => d.Metrics)
            .Include(d => d.Insights)
            .Include(d => d.Company)
            .FirstOrDefaultAsync(d => d.DatasetId == id && d.Company.UserId == userId);

        return dataset is null ? NotFound() : Ok(dataset);
    }

    [HttpPost("upload")]
    public async Task<ActionResult<Dataset>> UploadDataset([FromForm] IFormFile file, [FromForm] int companyId)
    {
        var userId = GetCurrentUserId();
        var ownsCompany = await _db.Companies.AnyAsync(c => c.CompanyId == companyId && c.UserId == userId);
        if (!ownsCompany)
        {
            return NotFound("Company not found.");
        }

        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!AllowedExtensions.Contains(ext))
        {
            return BadRequest("Only .csv, .xlsx, and .xls files are supported.");
        }

        var dataset = await _datasetService.SaveDatasetAsync(file, companyId);

        _ = Task.Run(async () =>
        {
            try
            {
                await _datasetService.ProcessDatasetAsync(dataset.DatasetId);
            }
            catch
            {
            }
        });

        return CreatedAtAction(nameof(GetDatasetById), new { id = dataset.DatasetId }, dataset);
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteDataset(int id)
    {
        var userId = GetCurrentUserId();
        var dataset = await _db.Datasets
            .Include(d => d.Company)
            .FirstOrDefaultAsync(d => d.DatasetId == id && d.Company.UserId == userId);

        if (dataset is null)
        {
            return NotFound();
        }

        if (System.IO.File.Exists(dataset.FilePath))
        {
            System.IO.File.Delete(dataset.FilePath);
        }

        _db.Datasets.Remove(dataset);
        await _db.SaveChangesAsync();

        return NoContent();
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

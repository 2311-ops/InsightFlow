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
[Route("api/companies")]
public class CompaniesController : ControllerBase
{
    private readonly AppDbContext _db;

    public CompaniesController(AppDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<Company>>> GetCompanies()
    {
        var userId = GetCurrentUserId();
        var companies = await _db.Companies.Where(c => c.UserId == userId).OrderBy(c => c.Name).ToListAsync();
        return Ok(companies);
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<Company>> GetCompany(int id)
    {
        var userId = GetCurrentUserId();
        var company = await _db.Companies.FirstOrDefaultAsync(c => c.CompanyId == id && c.UserId == userId);
        return company is null ? NotFound() : Ok(company);
    }

    [HttpPost]
    public async Task<ActionResult<Company>> CreateCompany([FromBody] CompanyUpsertRequest request)
    {
        var userId = GetCurrentUserId();
        var company = new Company
        {
            Name = request.Name,
            Industry = request.Industry,
            UserId = userId
        };

        _db.Companies.Add(company);
        await _db.SaveChangesAsync();
        return CreatedAtAction(nameof(GetCompany), new { id = company.CompanyId }, company);
    }

    [HttpPut("{id:int}")]
    public async Task<IActionResult> UpdateCompany(int id, [FromBody] CompanyUpsertRequest request)
    {
        var userId = GetCurrentUserId();
        var company = await _db.Companies.FirstOrDefaultAsync(c => c.CompanyId == id && c.UserId == userId);
        if (company is null)
        {
            return NotFound();
        }

        company.Name = request.Name;
        company.Industry = request.Industry;

        await _db.SaveChangesAsync();
        return NoContent();
    }

    [HttpDelete("{id:int}")]
    public async Task<IActionResult> DeleteCompany(int id)
    {
        var userId = GetCurrentUserId();
        var company = await _db.Companies.FirstOrDefaultAsync(c => c.CompanyId == id && c.UserId == userId);
        if (company is null)
        {
            return NotFound();
        }

        _db.Companies.Remove(company);
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

    public record CompanyUpsertRequest(string Name, string Industry);
}

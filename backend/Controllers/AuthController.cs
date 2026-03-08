using Microsoft.AspNetCore.Mvc;
using InsightFlow.Backend.Services;

namespace InsightFlow.Backend.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuthController : ControllerBase
{
    private readonly AuthService _authService;

    public AuthController(AuthService authService) => _authService = authService;

    // POST /api/auth/register
    [HttpPost("register")]
    public async Task<IActionResult> Register([FromBody] RegisterRequest req)
    {
        var user = await _authService.RegisterAsync(req.Email, req.Password, req.FirstName, req.LastName);
        if (user is null)
            return Conflict(new { message = "Email already registered." });

        return Ok(new { message = "Account created.", userId = user.UserId });
    }

    // POST /api/auth/login
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest req)
    {
        var token = await _authService.LoginAsync(req.Email, req.Password);
        if (token is null)
            return Unauthorized(new { message = "Invalid credentials." });

        return Ok(new { token });
    }
}

// ── Request DTOs ──────────────────────────────────────────────────
public record RegisterRequest(string Email, string Password, string FirstName, string LastName);
public record LoginRequest(string Email, string Password);

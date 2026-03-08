// Phase 2
using System.Text;

namespace InsightFlow.Backend.Services;

public class AIService
{
    private readonly HttpClient _httpClient;

    public AIService(HttpClient httpClient, IConfiguration configuration)
    {
        _httpClient = httpClient;
        _httpClient.BaseAddress = new Uri(configuration["AIEngine:BaseUrl"] ?? throw new InvalidOperationException("AIEngine:BaseUrl is required."));
        _httpClient.Timeout = TimeSpan.FromMinutes(5);
    }

    public async Task<string> ProcessFileAsync(string payloadJson)
    {
        using var content = new StringContent(payloadJson, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("/ai/process", content);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }

    public async Task<string> GetInsightAsync(string metricsJson)
    {
        using var content = new StringContent(metricsJson, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("/ai/insights", content);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }

    public async Task<string> AskQuestionAsync(string question, string metricsJson)
    {
        var payload = $$"""{"question":{{System.Text.Json.JsonSerializer.Serialize(question)}},"metrics":{{metricsJson}}}""";
        using var content = new StringContent(payload, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("/ai/ask", content);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }
}
